"""Codifica capturas de una demostracion real, conservando sus intervalos medidos."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools' / 'python'))
import imageio_ffmpeg


def main():
    directory = ROOT / 'output' / 'video'
    frames_dir = directory / 'frames'
    timeline = json.loads((frames_dir / 'timeline.json').read_text(encoding='utf-8'))
    frames = timeline['frames']
    if len(frames) < 2:
        raise RuntimeError('Faltan capturas de la demostracion.')
    lines = []
    for index, frame in enumerate(frames):
        path = frames_dir / frame['file']
        if not path.is_file():
            raise RuntimeError('Falta una captura: ' + str(path))
        lines.append("file '" + path.as_posix().replace("'", "'\\''") + "'")
        duration = frames[index + 1]['at'] - frame['at'] if index + 1 < len(frames) else 2.0
        lines.append(f'duration {max(0.04, duration):.6f}')
    lines.append(lines[-2])
    concat = frames_dir / 'concat.txt'
    concat.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    target = directory / 'Demostracion-GitOps-ArgoCD.mp4'
    args = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-hide_banner', '-loglevel', 'warning',
            '-f', 'concat', '-safe', '0', '-i', str(concat), '-vf', 'fps=15,scale=1280:-2',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(target)]
    subprocess.run(args, check=True)
    duration = frames[-1]['at'] - frames[0]['at'] + 2
    report = {'video': target.name, 'frames': len(frames), 'seconds': round(duration, 2),
              'method': 'Capturas del navegador durante operaciones reales. Intervalos conservados. Sin narracion.',
              'scenes': timeline.get('scenes', [])}
    (directory / 'grabacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
