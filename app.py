import streamlit as st
import openai
import textstat
from docx import Document
import io
import streamlit_authenticator as stauth
import language_tool_python
import difflib

# --- Authentication Setup ---
# Username: author
# Password: secret123

# 🔐 Replace this with your actual generated hash
hashed_passwords = ['secret123']

credentials = {
    "usernames": {
        "author": {
            "name": "Author",
            "password": hashed_passwords[0]
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "gpt_auth",      # cookie name
    "auth",          # key
    cookie_expiry_days=1
)

auth_result = authenticator.login(location='main')

if auth_result and auth_result['authenticated']:
    name = auth_result['name']
    authenticator.logout("Logout", "sidebar")
    st.success(f"Welcome, {name} 👋")

    st.set_page_config(page_title="GPT-Powered Fiction Proofreader", layout="wide")
    st.title("📖 GPT-Powered Fiction Proofreader")
    st.markdown("Upload a `.txt` or `.docx` file. I’ll proofread it for grammar, tone, and style using GPT-4 or LanguageTool.")

    # API key input for GPT
    api_key = st.sidebar.text_input("Enter your OpenAI API key (for GPT-4 proofreading)", type="password")
    uploaded_file = st.file_uploader("Choose your novel file", type=["txt", "docx"])

    def extract_text(file):
        if file.name.endswith(".txt"):
            return file.read().decode("utf-8")
        elif file.name.endswith(".docx"):
            doc = Document(file)
            return "\n".join([para.text for para in doc.paragraphs])
        return ""

    def analyze_paragraph_with_gpt(para):
        prompt = f"Please proofread this paragraph for grammar, spelling, clarity, tone, and style. Suggest edits if needed.\n\nParagraph:\n{para}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content'].strip()
        readability = {
            "flesch_reading_ease": textstat.flesch_reading_ease(para),
            "reading_level": textstat.text_standard(para, float_output=False),
            "sentence_count": textstat.sentence_count(para),
        }
        return reply, readability

    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1]
        try:
            raw_text = extract_text(uploaded_file)
        except Exception as e:
            st.error("Could not read the file.")
            raw_text = ""

        if not raw_text:
            st.warning("The file is empty or unreadable.")
        else:
            st.text_area("File Content:", raw_text, height=200)

            tab1, tab2 = st.tabs(["🤖 GPT-4 Proofread", "📝 LanguageTool Proofread"])

            with tab1:
                if api_key:
                    openai.api_key = api_key
                    if st.button("Run GPT-4 Proofread"):
                        with st.spinner("Analyzing your novel with GPT-4..."):
                            paragraphs = [p.strip() for p in raw_text.split("\n") if len(p.strip()) > 0]

                            report = []
                            for i, para in enumerate(paragraphs):
                                feedback, readability = analyze_paragraph_with_gpt(para)
                                report.append({
                                    "paragraph": para,
                                    "gpt_feedback": feedback,
                                    "readability": readability
                                })

                        for idx, section in enumerate(report):
                            st.markdown(f"### Paragraph {idx+1}")
                            st.markdown(section['paragraph'])
                            st.markdown("**🤖 GPT Feedback:**")
                            st.write(section['gpt_feedback'])
                            st.markdown("**📘 Readability Stats:**")
                            st.write(section['readability'])
                            st.markdown("---")

                        if st.button("📥 Download GPT-4 Report"):
                            buffer = io.StringIO()
                            for idx, section in enumerate(report):
                                buffer.write(f"\n--- Paragraph {idx+1} ---\n")
                                buffer.write(section['paragraph'] + "\n")
                                buffer.write("GPT Feedback:\n" + section['gpt_feedback'] + "\n")
                                buffer.write(str(section['readability']) + "\n")
                            st.download_button("Download .txt report", data=buffer.getvalue(), file_name="gpt_proofreading_report.txt", mime="text/plain")
                else:
                    st.warning("🔑 Please enter your OpenAI API key in the sidebar for GPT-4 proofreading.")

            with tab2:
                if st.button("Run LanguageTool Proofread"):
                    try:
                        tool = language_tool_python.LanguageTool('en-US')
                        tool._url = 'https://api.languagetool.org/v2/'  # Free public server

                        matches = tool.check(raw_text)
                        corrected = language_tool_python.utils.correct(raw_text, matches)

                        st.subheader("Original Text")
                        st.text_area("Before", raw_text, height=200)

                        st.subheader("Corrected Text")
                        st.text_area("After", corrected, height=200)

                        st.subheader("🔍 What Was Changed")
                        diff = difflib.ndiff(raw_text.split(), corrected.split())
                        changes = []

                        for word in diff:
                            if word.startswith("+ "):
                                changes.append(f"🟢 {word[2:]}")
                            elif word.startswith("- "):
                                changes.append(f"🔴 {word[2:]}")

                        if changes:
                            st.markdown("**Detected Changes:**")
                            st.write("\n".join(changes))
                        else:
                            st.success("No changes detected. Your text looks great!")

                        if st.button("📥 Download LanguageTool Report"):
                            buffer = io.StringIO()
                            buffer.write("Original Text:\n" + raw_text + "\n\n")
                            buffer.write("Corrected Text:\n" + corrected + "\n\n")
                            buffer.write("Changes:\n" + "\n".join(changes))
                            st.download_button("Download .txt report", data=buffer.getvalue(), file_name="languagetool_proofreading_report.txt", mime="text/plain")
                    except Exception as e:
                        st.error(f"Proofreading failed: {str(e)}")
else:
    st.warning("Please enter your credentials")
