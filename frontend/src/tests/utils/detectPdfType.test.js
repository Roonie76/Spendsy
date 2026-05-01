import { beforeEach, describe, expect, it, vi } from "vitest";

const getDocument = vi.fn();

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: {},
  OPS: {
    paintImageXObject: 1,
    paintInlineImageXObject: 2,
    paintJpegXObject: 3,
  },
  getDocument,
}));

vi.mock("pdfjs-dist/build/pdf.worker.mjs?url", () => ({
  default: "pdf.worker.mjs",
}));

const makeFile = () => new File(["%PDF"], "statement.pdf", { type: "application/pdf" });

const makePdf = ({ pages, metadata = {} }) => ({
  numPages: pages.length,
  getMetadata: vi.fn().mockResolvedValue({ info: metadata }),
  getPage: vi.fn((pageNumber) => Promise.resolve(pages[pageNumber - 1])),
});

const makePage = ({ text = "", fontName = "g_d0_f1", imageOps = [] }) => ({
  getTextContent: vi.fn().mockResolvedValue({
    items: text
      ? text.split(/\s+/).map((str) => ({ str, fontName }))
      : [],
  }),
  getOperatorList: vi.fn().mockResolvedValue({ fnArray: imageOps }),
});

describe("detectPdfType", () => {
  beforeEach(() => {
    getDocument.mockReset();
  });

  it("keeps high-text iLovePDF statements digital even when images exist", async () => {
    const { detectPdfType } = await import("../../utils/pdf/detectPdfType");
    const longText = Array.from({ length: 1200 }, (_, index) => `PNB${index}`).join(" ");
    const pages = Array.from({ length: 5 }, () =>
      makePage({ text: longText, imageOps: [1] }),
    );
    getDocument.mockReturnValue({
      promise: Promise.resolve(makePdf({
        pages,
        metadata: { Producer: "iLovePDF", Creator: "PNB ONE" },
      })),
    });

    await expect(detectPdfType(makeFile())).resolves.toBe("digital");
  });

  it("flags low-text Tesseract image PDFs as OCR", async () => {
    const { detectPdfType } = await import("../../utils/pdf/detectPdfType");
    getDocument.mockReturnValue({
      promise: Promise.resolve(makePdf({
        pages: [makePage({ imageOps: [1] })],
        metadata: { Producer: "Tesseract OCR" },
      })),
    });

    await expect(detectPdfType(makeFile())).resolves.toBe("ocr");
  });
});
