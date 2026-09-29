import os
from PIL import Image

"""
自动拼接为Sprite
"""

# 1. 设置图像文件夹路径与行列布局
image_folder = r"E:\Download\合成 1"
output_path = "sprite_sheet_0px.png"

# 2. 读取所有图片
images = [
    Image.open(os.path.join(image_folder, f))
    for f in sorted(os.listdir(image_folder))
    if f.endswith((".png", ".jpg"))
]
if not images:
    raise ValueError("未找到图片！")

img_w, img_h = images[0].size
total_imgs = len(images)
rows = 1

# 3. 创建 0 缝隙大图
sprite_sheet = Image.new("RGBA", (total_imgs * img_w, rows * img_h))

for idx, img in enumerate(images):
    c = idx % total_imgs
    r = idx // total_imgs
    # 精确平铺，无任何间距
    sprite_sheet.paste(img, (c * img_w, r * img_h))

sprite_sheet.save(output_path)
print(f"拼版成功！已保存至 {output_path}")