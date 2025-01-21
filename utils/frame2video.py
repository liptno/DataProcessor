import os
import cv2
import numpy as np
import OpenEXR
import Imath

def ACES(x, gamma_correct=True, gamma=2.2):

    ACESInputMat = np.array(
        [
            [0.59719, 0.35458, 0.04823],
            [0.07600, 0.90834, 0.01566],
            [0.02840, 0.13383, 0.83777],
        ]
    )

    ACESOutputMat = np.array(
        [
            [1.60475, -0.53108, -0.07367],
            [-0.10208, 1.10813, -0.00605],
            [-0.00327, -0.07276, 1.07602],
        ]
    )

    x = np.einsum("ji, hwi -> hwj", ACESInputMat, x)
    a = x * (x + 0.0245786) - 0.000090537
    b = x * (0.983729 * x + 0.4329510) + 0.238081
    x = a / b
    x = np.einsum("ji, hwi -> hwj", ACESOutputMat, x)

    if gamma_correct:
        return np.power(np.clip(x, 0.0, 1.0), 1.0 / gamma)
    else:
        return x

def read_exr(exr_path):
    """
    读取EXR格式的HDR图片。
    """
    file = OpenEXR.InputFile(exr_path)
    dw = file.header()['dataWindow']
    size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)

    # 读取三个通道
    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
    (R,G,B) = [np.frombuffer(file.channel(c, FLOAT), dtype=np.float32) for c in 'RGB']
    
    # 重塑数组为RGB顺序（ACES需要RGB顺序）
    rgb = np.zeros((size[1], size[0], 3), dtype=np.float32)
    rgb[..., 0] = R.reshape(size[1], size[0])  # R通道
    rgb[..., 1] = G.reshape(size[1], size[0])  # G通道
    rgb[..., 2] = B.reshape(size[1], size[0])  # B通道
    
    return rgb

def tone_mapping(hdr_img, gamma=2.2, exposure=1.0):
    """
    使用ACES进行色调映射。
    """
    # 应用曝光
    img = hdr_img * exposure
    
    # 应用ACES色调映射
    img = ACES(img, gamma_correct=True, gamma=gamma)
    
    # 转换为BGR顺序（OpenCV需要）并转换为8位整数
    img = img[..., ::-1]  # RGB到BGR
    return (img * 255).astype(np.uint8)

def frames_to_video(frame_dir, output_video_path, fps=30, gamma=2.2, exposure=1.0):
    """
    将帧连接在一起生成视频。

    参数:
    frame_dir (str): 帧所在的目录
    output_video_path (str): 输出视频文件的路径
    fps (int): 视频的帧率
    gamma (float): HDR转换时的gamma值
    exposure (float): HDR转换时的曝光值
    """
    # 获取所有帧文件
    frame_files = sorted([os.path.join(frame_dir, f) for f in os.listdir(frame_dir) 
                         if f.endswith(('.png', '.jpg', '.exr'))])

    if not frame_files:
        raise ValueError(f"No frames found in directory {frame_dir}")

    is_hdr = frame_files[0].endswith('.exr')
    # 读取第一帧以获取帧的尺寸
    if is_hdr:
        first_frame = read_exr(frame_files[0])
        first_frame = tone_mapping(first_frame, gamma, exposure)
    else:
        first_frame = cv2.imread(frame_files[0])
    
    height, width, _ = first_frame.shape

    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    for frame_file in frame_files:
        if is_hdr:
            frame = read_exr(frame_file)
            frame = tone_mapping(frame, gamma, exposure)
        else:
            frame = cv2.imread(frame_file)
            
        writer.write(frame)

    writer.release()
    print(f"Video saved to {output_video_path}")

if __name__ == "__main__":
    # HDR示例
    frames_to_video(r"G:\optix\output_motion",
                   r"G:\optix\video\bistro1_0116_motion.mp4",
                   gamma=2.2,
                   exposure=1.0)


