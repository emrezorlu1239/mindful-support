import sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root),str(root/'tests')]
os.environ['MINDFUL_DB_PATH']=str(root/'work/js-fixture.sqlite')
from app import build_app
from ai.runtime import AIRuntime
from test_ai_pipeline import Model,References
import uvicorn
if __name__ == '__main__':
    uvicorn.run(build_app(AIRuntime(Model(),References())),host='127.0.0.1',port=18765,access_log=False,log_level='error')
