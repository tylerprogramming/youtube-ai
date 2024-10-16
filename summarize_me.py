from openai import OpenAI

class OpenAIAssistant:
    def __init__(self, context):
        self.client = OpenAI()
        self.context = context

    def ask_question(self, question):
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant.  You are given a context and a question.  You must answer the question based on the context.  If the context is not relevant to the question, you must say so.  If the context is relevant to the question, you must answer the question based on the context."},
                {"role": "user", "content": f"The context: {self.context} \n\n The question: {question}"}
            ]
        )

        return completion.choices[0].message.content

# Usage example:
# assistant = OpenAIAssistant()
# response = assistant.ask_question("What is a LLM?")