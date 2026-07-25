from app.services.retriever_service import RetrieverService


def main():

    lesson = "المحاليل المائية"

    content = RetrieverService.retrieve_lesson_content(lesson)

    print("=" * 50)
    print("RETRIEVAL SUCCESS")
    print("=" * 50)

    print("Characters:", len(content))

    print("\nFIRST 1000 CHARACTERS:")
    print(content[:1000])


if __name__ == "__main__":
    main()