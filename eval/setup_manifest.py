import os
import json
import glob

def build_manifest():
    img_dir = 'data/sroie_subset/img'
    key_dir = 'data/sroie_subset/key'
    
    if not os.path.exists(img_dir) or not os.path.exists(key_dir):
        print("ERROR: SROIE dataset not found locally.")
        return

    img_files = sorted(glob.glob(os.path.join(img_dir, '*.jpg')))
    
    manifest = []
    
    for img_path in img_files:
        base_name = os.path.basename(img_path).replace('.jpg', '')
        key_path = os.path.join(key_dir, f"{base_name}.txt")
        
        if os.path.exists(key_path):
            with open(key_path, 'r', encoding='utf-8') as f:
                try:
                    gt = json.load(f)
                    manifest.append({
                        "source_id": base_name,
                        "file_path": img_path,
                        "ground_truth_merchant": gt.get("company", ""),
                        "ground_truth_date": gt.get("date", ""),
                        "ground_truth_amount": gt.get("total", "")
                    })
                except json.JSONDecodeError:
                    pass
                    
        if len(manifest) == 20: # 15-20 held out documents
            break
            
    if not manifest:
        # Create an empty template/schema to demonstrate the expected structure
        manifest = [{
            "source_id": "EXAMPLE_ID_X51005230616",
            "file_path": "data/sroie_subset/img/EXAMPLE_ID_X51005230616.jpg",
            "ground_truth_merchant": "EXAMPLE MERCHANT",
            "ground_truth_date": "2018-12-28",
            "ground_truth_amount": "12.00"
        }]
        print("Dataset missing. Generated a template manifest.")
        
    os.makedirs('eval', exist_ok=True)
    with open('eval/manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Generated eval/manifest.json.")

if __name__ == '__main__':
    build_manifest()
