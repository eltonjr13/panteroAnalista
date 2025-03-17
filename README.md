# Analisador de PDF com Chatbot

Uma aplicação Flask que permite fazer upload de PDFs e interagir com um chatbot baseado na API da OpenAI para responder perguntas sobre o conteúdo.

## Funcionalidades
- Upload de PDFs com limite de 5MB.
- Extração de texto com PyPDF2.
- Chatbot alimentado por OpenAI para respostas contextuais.
- Interface em preto e branco inspirada no Grok.
- Geração de arquivo `.txt` com texto bruto.

## Pré-requisitos
- Python 3.8+
- Chave da API da OpenAI

## Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu_usuario/pdf-chatbot.git
   cd pdf-chatbot