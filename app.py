from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    # Esto busca el archivo en la carpeta 'templates'
    return render_template('pagina_principal.html')

if __name__ == '__main__':
    # Corremos en el puerto 5000 para no chocar con la API (puerto 8000)
    print("🌍 Dashboard corriendo en: http://localhost:5000")
    app.run(debug=True, port=5000)