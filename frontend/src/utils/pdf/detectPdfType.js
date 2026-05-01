import * as pdfjsLib from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';

// Configure the worker explicitly using local bundle instead of CDN
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export const detectPdfType = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

    const metadataResult = await pdf.getMetadata().catch(() => ({}));
    const metadata = metadataResult?.info || {};
    const combinedMeta = `${metadata.Producer || ""} ${metadata.Creator || ""}`.toLowerCase();

    // Scan past sparse cover/logo pages; stop early once high text volume
    // proves the file is native.
    const numPagesToCheck = pdf.numPages;
    let totalTextLength = 0;
    let totalWords = 0;
    const fontNames = new Set();
    let imageOperationCount = 0;

    for (let i = 1; i <= numPagesToCheck; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        const pageText = (textContent.items || [])
            .map(item => (item.str !== undefined ? item.str : ""))
            .join(' ');

        const cleanText = pageText.replace(/[^A-Za-z0-9]/g, '');
        totalTextLength += cleanText.length;
        totalWords += pageText.trim() ? pageText.trim().split(/\s+/).length : 0;

        for (const item of textContent.items || []) {
          if (item.fontName) fontNames.add(item.fontName);
        }

        const operatorList = await page.getOperatorList().catch(() => null);
        if (operatorList?.fnArray) {
          imageOperationCount += operatorList.fnArray.filter((fn) =>
            fn === pdfjsLib.OPS.paintImageXObject ||
            fn === pdfjsLib.OPS.paintInlineImageXObject ||
            fn === pdfjsLib.OPS.paintJpegXObject
          ).length;
        }

        if (totalTextLength > 5000) return "digital";
    }

    const avgCharsPerPage = totalTextLength / Math.max(numPagesToCheck, 1);
    const wordsPerPage = totalWords / Math.max(numPagesToCheck, 1);

    const scoreTextDensity = avgCharsPerPage > 500 ? 0 : avgCharsPerPage > 200 ? 0.2 : avgCharsPerPage > 50 ? 0.7 : 1;
    const scoreFontPresence = fontNames.size >= 3 ? 0 : fontNames.size === 2 ? 0.2 : fontNames.size === 1 ? 0.6 : 1;
    const scoreWordSelectability = wordsPerPage > 80 ? 0 : wordsPerPage > 30 ? 0.3 : wordsPerPage > 5 ? 0.7 : 1;

    const ocrKeywords = ["tesseract", "abbyy", "adobe acrobat ocr", "nuance", "readiris", "omnipage"];
    const utilityKeywords = ["ilovepdf", "smallpdf", "pdf24", "sejda", "pdfescape", "ghostscript", "microsoft", "libreoffice", "reportlab", "fpdf", "wkhtmltopdf"];
    const scoreProducerMeta = ocrKeywords.some(k => combinedMeta.includes(k))
      ? 1
      : utilityKeywords.some(k => combinedMeta.includes(k))
        ? 0
        : 0.5;

    // pdfjs exposes image draw operations, not reliable bounding boxes. Treat
    // image presence as weak OCR evidence unless text density is also poor.
    const imageOpsPerPage = imageOperationCount / Math.max(numPagesToCheck, 1);
    const scoreImageCoverage = imageOpsPerPage === 0 ? 0 : avgCharsPerPage > 200 ? 0.1 : imageOpsPerPage > 0.8 ? 0.7 : 0.3;

    const score =
      0.35 * scoreTextDensity +
      0.20 * scoreFontPresence +
      0.20 * scoreImageCoverage +
      0.15 * scoreProducerMeta +
      0.10 * scoreWordSelectability;

    return score >= 0.55 ? "ocr" : "digital";
  } catch (error) {
    console.error("Error analyzing PDF with pdfjs-dist:", error);
    // If we fail to detect, assume digital to let the backend try parsing
    return "digital";
  }
};
