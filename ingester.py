"""ROS Cadastral Parcels PostgreSQL updater."""

import os
import zipfile
import glob

from sandbox_ingest import OGRUpdater, zip_into_one_file
from sandbox_definitions import CadastralParcel
from ogr_definitions import CadastralParcelLayer, ROSCadastralParcelsInfo
from download import download_files
import info

class ParcelUpdater(OGRUpdater):
    """Updater that downloads OS Open Roads (GML3) and ingests it."""

    def __init__(self) -> None:
        """Initialise with a table name, file path, and connection defaults."""
        OGRUpdater.__init__(
            self,
            info.provider,
            info.source,
            ROSCadastralParcelsInfo,
            {CadastralParcel : CadastralParcelLayer},
            ".shp",
        )
        self.real_id = "inspireid"

    def extract_files_to_process(self, tmpdir:str) -> list[str]:
        for i in glob.glob("**/*.zip", root_dir=tmpdir, recursive=True):
            found = os.path.join(tmpdir, i)
            with zipfile.ZipFile(found, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
        shp_files = glob.glob("**/*_bng.shp", root_dir=tmpdir, recursive=True)
        return shp_files

    def poll_data(self, tmp_folder:str) -> str:
        """Return the path to the OS Open Roads zip archive, downloading if needed."""
        files = download_files(tmp_folder)
        allzip = os.path.join(tmp_folder, "ros_cad_files.zip")
        zip_into_one_file(allzip, files)
        return allzip


if __name__ == "__main__":
    u = ParcelUpdater()
    u.process()
