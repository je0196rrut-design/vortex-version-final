from flask import Flask, render_template

app = Flask(__name__)

# 1. RUTA GERENTE
@app.route('/')
def dashboard():
    return render_template('manager.html')

# 2. RUTA AGENTE
@app.route('/inbox')
def inbox():
    return render_template('inbox.html')

# 3. RUTA CLIENTE
@app.route('/portal')
def portal():
    return render_template('client_portal.html')

if __name__ == '__main__':
    print("🚀 Vortex Ecosystem Iniciado")
    print("📊 Manager: http://localhost:5000/")
    print("📨 Agente:  http://localhost:5000/inbox")
    print("🙋 Cliente: http://localhost:5000/portal")
    app.run(debug=True, port=5000)