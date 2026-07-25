import io
import re
import os

import fitz
import chromadb
import pytesseract

from PIL import Image
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.constants import LESSONS


# ==========================================================
# Windows multiprocessing fix
# ==========================================================

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==========================================================
# Embedding model
# ==========================================================

model = SentenceTransformer("all-MiniLM-L6-v2",device="cpu")

# ==========================================================
# Manual corrections
# ==========================================================

EQUATION_FIXES = {
    12: "\nCorrect equations: HCl -> H+ + Cl-  |  CH3COOH <-> CH3COO- + H+",

    20: "\nCorrect equation: NaOH -> Na+ + OH-",

    28: "\nCorrect equation: NH3(g) + HCl(g) -> NH4Cl(s)",

    32: "\nCorrect equation: Fe(s) + CuSO4(aq) -> FeSO4(aq) + Cu(s)",

    35: "\nCorrect equation: NaCl(aq) + AgNO3(aq) -> AgCl(s) + NaNO3(aq)",

    42: """
Correct equations:
NaOH(aq) + HCl(aq) -> NaCl(aq) + H2O(l)
2Na(s) + Cl2(g) -> 2NaCl(s)
Zn(s) + 2HCl(aq) -> ZnCl2(aq) + H2(g)
""",

    43: """
Correct equations:
H2SO4(aq) + Na2CO3(aq) -> Na2SO4(aq) + H2O(l) + CO2(g)
NH4Cl(aq) + AgNO3(aq) -> NH4NO3(aq) + AgCl(s)
Fe(s) + CuSO4(aq) -> FeSO4(aq) + Cu(s)
""",
}


FULL_OVERRIDES = {

    24: """
Self-test - Basic solutions:
1. Number of basic functions in barium hydroxide: a.1  b.4  c.2  d.3
2. One of the following bases is used to treat stomach acidity: a. NaOH  b. Mg(OH)2  c. KOH  d. NH4OH
3. The base solution with the highest electrical conductivity among equal-concentration solutions: a. aluminum hydroxide  b. sodium hydroxide  c. ammonium hydroxide  d. iron(III) hydroxide
4. Ionic formula of ammonium hydroxide: a. NH4+ + OH-  b. 4NH+ + OH-  c. NH4O- + H+  d. NH4OH
""",

    38: """
Question 6 - Match the reaction type with its general formula:

Combination:
A + B -> C

Decomposition:
A -> B + C

Displacement:
A + BC -> AC + B

Double displacement:
AB + CD -> AD + CB
""",

    70: """
Self-test - Alkanes:

1. Formula of methane:
a. CH4  b. C2H6  c. C3H8  d. CH3

2. General formula of alkanes:
a. CnH2n+2  b. CnH2n  c. CnH2n-2  d. CnH2n+1

Complete the table:
methane, propane, hexane
""",

    75: """
Alkyne formula table:

Compound: propyne

Molecular formula:
C3H4

Condensed formula:
H3C-C#CH
""",

    92: """
Uranium isotope used to determine the age of the Earth:
U-238
"""
}


# ==========================================================
# Indexing Service
# ==========================================================

class IndexingService:

    @staticmethod
    def get_client():
        return chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)


    @staticmethod
    def get_collection():
        client = IndexingService.get_client()
        return client.get_or_create_collection(
            name="chemistry_material",
            embedding_function=None,
            metadata={
                "hnsw:space": "cosine"
            }
        )
    # ------------------------------------------------------

    @staticmethod
    def clean_text(text: str):
        text = text.replace("\n", " ")
        # remove Arabic tatweel
        text = re.sub(r"\u0640+","",text)
        return " ".join(text.split())
    # ------------------------------------------------------

    @staticmethod
    def looks_like_data_table(text,digit_threshold=8):
        digits = len(re.findall(r"\d",text))
        return digits >= digit_threshold

    # ------------------------------------------------------

    @staticmethod
    def extract_page_text(page,page_num,ocr_min_length=20):
        text = page.get_text()

        # normal PDF text
        if len(text.strip()) >= ocr_min_length:
            return text, "native"

        # OCR fallback
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        ocr_text = pytesseract.image_to_string(img,lang="ara").strip()

        if len(ocr_text) < ocr_min_length:
            return (
                f"[Page {page_num}: visual content - needs manual description]",
                "needs_manual_review"
            )

        if IndexingService.looks_like_data_table(ocr_text):
            return (ocr_text,"needs_manual_review_table")

        return (ocr_text,"ocr")
    # ------------------------------------------------------

    @staticmethod
    def create_chunks(text,size=400,overlap=80):
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            chunk = words[start:start + size]
            chunks.append(" ".join(chunk))

            if start + size >= len(words):
                break

            start += size - overlap
        return chunks

    # ------------------------------------------------------
    # Extract lesson text from PDF
    # ------------------------------------------------------

    @staticmethod
    def extract_lesson_text(pdf_path,start_page,end_page):
        print(f"Opening PDF: {pdf_path}, pages {start_page}-{end_page}")
        doc = fitz.open(pdf_path)
        full_text = ""
        flagged_empty = []
        flagged_tables = []

        for i in range(start_page,min(end_page + 1, len(doc))):
            page_num = i + 1
            text, source = IndexingService.extract_page_text(doc[i],page_num)

            # Replace broken pages manually
            if page_num in FULL_OVERRIDES:
                text = FULL_OVERRIDES[page_num]
            elif page_num in EQUATION_FIXES:
                text += EQUATION_FIXES[page_num]
            full_text += text + " "

            # keep track of problematic pages
            if source == "needs_manual_review":
                flagged_empty.append(page_num)
            elif (
                source == "needs_manual_review_table"
                and page_num not in EQUATION_FIXES
                and page_num not in FULL_OVERRIDES
            ):
                flagged_tables.append(page_num)
        doc.close()
        print(f"Extracted text length: {len(full_text)}")
        return (
            IndexingService.clean_text(full_text),
            flagged_empty,
            flagged_tables
        )

    # ------------------------------------------------------
    # Index all lessons into ChromaDB
    # ------------------------------------------------------

    @staticmethod
    def index_all_lessons():
        print("LESSONS:",LESSONS)
        collection = IndexingService.get_collection()
        all_flagged_empty = {}
        all_flagged_tables = {}
        for lesson, pages in LESSONS.items():
            print(f"\nIndexing lesson={lesson}, pages={pages}")
            text, empty, tables = IndexingService.extract_lesson_text(
                settings.CHEMISTRY_PDF_PATH,
                pages[0],
                pages[1],
            )
            print(f"  text length: {len(text)}")
            chunks = IndexingService.create_chunks(text)
            print(f"  chunks: {len(chunks)}")

            # -------------------------
            # Generate embeddings
            # -------------------------

            print("Generating embeddings...")
            embeddings = model.encode(
                chunks,
                batch_size=8,
                show_progress_bar=False
            ).tolist()

            before = collection.count()

            collection.add(
                documents=chunks,
                embeddings=embeddings,
                ids=[
                    f"{lesson}_{i}"
                    for i in range(len(chunks))
                ],
                metadatas=[
                    {
                        "lesson": lesson,
                        "chunk_index": i
                    }
                    for i in range(len(chunks))
                ]
            )
            after = collection.count()
            print(f"  collection count before={before}, after={after}")

            if empty:
                all_flagged_empty[lesson] = empty
            if tables:
                all_flagged_tables[lesson] = tables

        print("\nIndexing completed.")
        return (all_flagged_empty,all_flagged_tables)


    # ------------------------------------------------------
    # Verify indexing result
    # ------------------------------------------------------

    @staticmethod
    def verify_index():
        collection = IndexingService.get_collection()
        print("\n========== INDEX VERIFICATION ==========\n")
        total = 0
        for lesson in LESSONS:
            result = collection.get(
                where={"lesson": lesson})
            count = len(result["ids"])
            total += count
            if count > 0:
                print(f"✅ {lesson}: {count} chunks")
            else:
                print(f"❌ {lesson}: MISSING")
        print("\nTotal chunks:",total)
        print("\n========================================")