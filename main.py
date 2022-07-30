
from flask import Flask, render_template
from flask_restful import Api

from backend import preprocess

app = Flask(__name__, static_folder='frontend/dist/static', template_folder='frontend/dist')
api = Api(app)
api.add_resource(preprocess.SearchTrend, '/trend') 
api.add_resource(preprocess.SearchAnalyze, '/search_analyze') 

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')

if __name__ == '__main__':
    app.run()

'''
#app = create_app()


from flask import Flask, render_template

#from backend import create_app

if __name__=='__main__':
    app.run(debug=True)
'''