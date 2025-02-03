import os
import requests
import openai
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, session

# Inicjalizacja aplikacji Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Potrzebne do korzystania z sesji

# Pobieranie klucza API OpenAI z zmiennych środowiskowych
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_summary_with_model(text):
    """
    Funkcja do generowania podsumowania za pomocą GPT-4o-mini z wykorzystaniem OpenAI API.
    """
    prompt = (
        "You are an advanced AI specializing in summarizing website content. "
        "Your task is to generate a detailed, structured summary of the provided text. "
        "Your response should be at least 250 words long and cover the key points, "
        "including main topics, conclusions, and important details. Maintain logical flow and clarity.\n\n"
        "Write youe summary in polish\n\n"
        "Here is the text to summarize:\n\n"
        f"{text}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000  # Zwiększamy limit tokenów, aby generować dłuższe podsumowania
        )

        if response and 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']

        return "Nie udało się odczytać podsumowania z odpowiedzi modelu."

    except Exception as e:
        print(f"Błąd podczas generowania podsumowania: {e}")
        return None

def ask_questions_about_summary(summary, question):
    """
    Funkcja umożliwiająca zadawanie pytań do modelu dotyczących podsumowanej treści.
    """
    prompt = (
        f"Here is a summary of a webpage:\n\n{summary}\n\n"
        f"User's question: {question}\n\n"
        "Provide a detailed answer based on the summary in polish."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500  # Ograniczamy długość odpowiedzi na pytania
        )

        if response and 'choices' in response and response['choices']:
            return response['choices'][0]['message']['content']
        else:
            return "Model nie był w stanie odpowiedzieć na to pytanie."

    except Exception as e:
        print(f"Błąd podczas przetwarzania pytania: {e}")
        return None

def get_cleaned_text_from_url(url):
    """
    Funkcja do pobierania strony i czyszczenia jej tekstu.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Usuwamy niepotrzebne tagi
        for irrelevant in soup.body(['script', 'style', 'img', 'input']):
            irrelevant.decompose()

        text = soup.get_text()

        # Usuwamy puste linie
        cleaned_text = '\n'.join([line for line in text.splitlines() if line.strip() != ''])
        return cleaned_text

    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania strony: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    summary = session.get("summary")
    qa_history = session.get("qa_history", [])  # Nowa lista przechowująca historię pytań i odpowiedzi

    if request.method == "POST":
        # Rozróżniamy, który przycisk został naciśnięty
        if "generate" in request.form:
            url = request.form.get("url", "").strip()
            if url:
                page_text = get_cleaned_text_from_url(url)
                if page_text:
                    summary = generate_summary_with_model(page_text)
                    session["summary"] = summary
                    # Resetuj historię pytań i odpowiedzi przy nowym podsumowaniu
                    session["qa_history"] = []
                else:
                    summary = "Nie udało się pobrać lub przetworzyć treści strony."
            else:
                summary = "Podaj poprawny link, szefie."

        elif "ask" in request.form:
            question = request.form.get("question", "").strip()
            if not summary:
                qa_history.insert(0, {
                    "question": question,
                    "answer": "Nie znaleziono podsumowania. Najpierw wygeneruj podsumowanie, podając link."
                })
            elif question:
                answer = ask_questions_about_summary(summary, question)
                if answer:
                    # Dodajemy nowe pytanie i odpowiedź do historii
                    qa_history.insert(0, {"question": question, "answer": answer})
                    session["qa_history"] = qa_history

    return render_template("index.html", summary=summary, qa_history=qa_history)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
