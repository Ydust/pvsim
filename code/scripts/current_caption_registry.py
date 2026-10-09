"""Current caption exports only; no calculation or figure alteration."""
from pathlib import Path
import json
O=Path(__file__).resolve().parent
def write_main_caption(number):
    text=json.loads((O/'caption_registry.json').read_text(encoding='utf-8'))['main'][str(number)]
    folder=O/f'Figure_{number}';folder.mkdir(exist_ok=True)
    (folder/f'Figure_{number}_caption_en.txt').write_text(text.split('. ',1)[1]+'\n',encoding='utf-8')
if __name__=='__main__':
    for number in range(1,6):write_main_caption(number)
