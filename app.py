from flask import Flask, request, render_template, send_from_directory
import PyPDF2
import os
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

app = Flask(__name__)


UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Limite de 5MB para uploads

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não configurada no arquivo .env")
client = OpenAI(api_key=OPENAI_API_KEY)

pdf_data = {}  # {filename: {"text": texto, "messages": [...], "timestamp": tempo}}

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        raise Exception(f"Erro ao extrair texto do PDF: {str(e)}")

def get_openai_response(pdf_text, question):
    # Sanitizar a pergunta (remover caracteres potencialmente perigosos)
    question = ''.join(c for c in question if c.isprintable())
    if not question or len(question) > 500:  # Limite de 500 caracteres
        return "Pergunta inválida ou muito longa."
    
    try:
        prompt = f"Baseado no seguinte texto extraído de um PDF:\n\n{pdf_text}\n\nResponda à pergunta: {question}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente que responde perguntas com base em documentos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro ao consultar a OpenAI: {str(e)}"

def save_basic_results_to_txt(filename, text):
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_basic_results.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Texto Extraído do PDF\n")
        f.write("====================\n\n")
        f.write(text[:10000])
    return output_path

def cleanup_old_pdfs():
    current_time = time.time()
    expired = [filename for filename, data in pdf_data.items() if current_time - data["timestamp"] > 3600]
    for filename in expired:
        del pdf_data[filename]

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error="Nenhum arquivo enviado"), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return render_template('index.html', error="Nenhum arquivo selecionado"), 400
        
        if not file.filename.endswith('.pdf'):
            return render_template('index.html', error="Por favor, envie um arquivo PDF"), 400
        
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extrair texto
            text = extract_text_from_pdf(file_path)
            pdf_data[filename] = {
                "text": text,
                "messages": [{"type": "bot", "content": "PDF processado! Pergunte-me qualquer coisa sobre o conteúdo."}],
                "timestamp": time.time()
            }
            
            # Salvar resultados básicos
            txt_path = save_basic_results_to_txt(filename, text)
            
            os.remove(file_path)
            cleanup_old_pdfs()  # Limpar PDFs antigos
            
            return render_template('chat.html', filename=filename, messages=pdf_data[filename]["messages"], txt_path=txt_path)
        
        except Exception as e:
            os.remove(file_path) if os.path.exists(file_path) else None
            return render_template('index.html', error=f"Erro ao processar o arquivo: {str(e)}"), 500
    
    return render_template('index.html', error=None)

@app.route('/chat/<filename>', methods=['POST'])
def chat(filename):
    if filename not in pdf_data:
        return render_template('index.html', error="PDF não encontrado. Faça upload novamente."), 404
    
    pdf_text = pdf_data[filename]["text"]
    question = request.form.get('question', '').strip()
    
    if not question:
        pdf_data[filename]["messages"].append({"type": "bot", "content": "Por favor, faça uma pergunta!"})
    else:
        pdf_data[filename]["messages"].append({"type": "user", "content": question})
        answer = get_openai_response(pdf_text, question)
        pdf_data[filename]["messages"].append({"type": "bot", "content": answer})
    
    txt_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{filename}_basic_results.txt")
    cleanup_old_pdfs()  # Limpar PDFs antigos
    return render_template('chat.html', filename=filename, messages=pdf_data[filename]["messages"], txt_path=txt_path)

@app.route('/output/<filename>')
def serve_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug)