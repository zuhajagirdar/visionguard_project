import zipfile
import os
import json
import shutil

zip_path = r'C:\Users\zuhaj\OneDrive\Documents\Desktop\archive.zip'
img_dest = 'data/sroie_subset/img'
key_dest = 'data/sroie_subset/key'

os.makedirs(img_dest, exist_ok=True)
os.makedirs(key_dest, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as z:
    # Find all entities in test set
    entity_files = [f for f in z.namelist() if f.startswith('SROIE2019/test/entities/') and f.endswith('.txt')]
    
    count = 0
    for entity_file in entity_files:
        if count >= 20:
            break
            
        base_name = os.path.basename(entity_file)
        img_file = f"SROIE2019/test/img/{base_name.replace('.txt', '.jpg')}"
        
        # Check if corresponding image exists
        if img_file in z.namelist():
            # Extract and copy
            z.extract(entity_file, 'tmp_eval')
            z.extract(img_file, 'tmp_eval')
            
            shutil.copy(os.path.join('tmp_eval', entity_file), os.path.join(key_dest, base_name))
            shutil.copy(os.path.join('tmp_eval', img_file), os.path.join(img_dest, base_name.replace('.txt', '.jpg')))
            
            count += 1
            
print(f"Extracted {count} document pairs from ZIP to data/sroie_subset.")
shutil.rmtree('tmp_eval', ignore_errors=True)
