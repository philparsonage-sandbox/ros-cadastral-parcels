"""Source URL for the Countries (December 2023) Boundaries UK BFE dataset."""

from sandbox_ingest import DataSource, DataProvider

URL = "https://ros-inspire.themapcloud.com/"

provider: DataProvider = DataProvider(
    name="scotgov", label="Scottish Government"
)

source: DataSource = DataSource(
    url=URL,
    name="cad_parcels",
    label="RoS INSPIRE Cadastral Parcels",
    description="FRoS INSPIRE Cadastral Parcels",
    license="Custom",
    provider="scotgov"
)
