import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("MY Document question answering")
st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_kev = st.secrets.OPENAI_API_KEY

client = OpenAI(api_key=openai_api_kev)

# Sidebar Options
summary_type = st.sidebar.selectbox(
    "Choose summary type:",
    (
        "Summarize in 100 words",
        "Summarize in 2 connecting paragraphs",
        "Summarize in 5 bullet points",
    )
)

use_advanced = st.sidebar.checkbox("Use advanced model")

if use_advanced:
    model = "gpt-4o"
else:
    model = "gpt-4o-mini"

# Let the user upload a file via `st.file_uploader`.
uploaded_file = st.file_uploader(
    "Upload a document (.txt or .md)", type=("txt", "md")
)

if uploaded_file:

    # Process the uploaded file and question.
    document = uploaded_file.read().decode()

    if summary_type == "Summarize in 100 words":
        instruction = "Summarize the document in exactly 100 words."
    elif summary_type == "Summarize in 2 connecting paragraphs":
        instruction = "Summarize the document in 2 connecting paragraphs."
    else:
        instruction = "Summarize the document in 5 concise bullet points."

        messages = [
        {
            "role": "user",
            "content": f"Here's a document: {document} \n\n---\n\n {instruction}",
        }
    ]

    # Generate an answer using the OpenAI API.
    stream = client.chat.completions.create(
        model="model",
        messages=messages,
        stream=True,
    )

    # Stream the response to the app using `st.write_stream`.
    st.write_stream(stream)