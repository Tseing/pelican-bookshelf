import os
import shutil


def render_output(path: str) -> None:
    """Rename generated file into `*_output` and fetch original file from `backup`.

    Parameters
    ----------
    path : str
        Path of generated file.
    """
    file_dir, file_affix = os.path.splitext(path)
    output_name = "".join([file_dir, "_output", file_affix])
    try:
        os.remove(output_name)
    except FileNotFoundError:
        pass
    os.rename(path, output_name)

    backup_dir = "./backup"
    file_name = os.path.split(path)[-1]
    backup_file = os.path.join(backup_dir, file_name)
    shutil.copy(backup_file, path)
