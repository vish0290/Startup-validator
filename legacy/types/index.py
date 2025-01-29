from typing import TypedDict, Any

class UserInput(TypedDict):
    question: str

class Response(TypedDict):
    answer: str
    context: Any  # You can specify a more precise type if needed

class Document(TypedDict):
    title: str
    content: str