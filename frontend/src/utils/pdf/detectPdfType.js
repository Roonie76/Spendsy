import * as pdfjsLib from 'pdfjs-dist';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';

// Configure the worker explicitly using local bundle instead of CDN
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

export const detectPdfType = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    
    // Check first 2 pages (or 1 if only 1 page)
    const numPagesToCheck = Math.min(2, pdf.numPages);
    let totalTextLength = 0;

    for (let i = 1; i <= numPagesToCheck; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        
        // Extract plain text string
        // Extract plain text string safely
        const pageText = (textContent.items || [])
            .map(item => (item.str !== undefined ? item.str : ""))
            .join(' ');
        
        // Count meaningful alphanumeric characters
        const cleanText = pageText.replace(/[^A-Za-z0-9]/g, '');
        totalTextLength += cleanText.length;
    }

    // Heuristic: If we found less than 150 alphanumeric chars in the first two pages,
    // it's highly likely to be a scanned (OCR) PDF rather than a digital one.
    if (totalTextLength < 150) {
        return "ocr";
    }
    
    return "digital";
  } catch (error) {
    console.error("Error analyzing PDF with pdfjs-dist:", error);
    // If we fail to detect, assume digital to let the backend try parsing
    return "digital";
  }
};
