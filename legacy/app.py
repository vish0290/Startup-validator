import streamlit as st
from rag import get_response, retriever

def main():
    st.title("Startup Advisor")
    st.write("Your one-stop shop for all startup-related queries.")

    user_input = st.text_input("Your Question:")
    
    if st.button("Get Answer"):
        if user_input:
            with st.spinner("Fetching the answer..."):
                response = get_response(user_input, retriever)
            st.write("Answer:", response)
        else:
            st.warning("Please enter a question.")

if __name__ == "__main__":
    main()