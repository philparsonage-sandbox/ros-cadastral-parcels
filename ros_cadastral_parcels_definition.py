from geoalchemy2 import Geometry
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String
from sandbox_ingest import base_definitions

DATA_SOURCE: str = "ros_inspire" 


class CadastralParcel(
    base_definitions.generate_base(DATA_SOURCE), SQLModel, table=True
):
    """A cadastral parcel"""

    __tablename__ = DATA_SOURCE + "_cadastral_parcels"
    __description__ = "blah blah blah"
    id: str | None = Field(
        default=None,
        sa_column=Column(String, primary_key=True, info={"source": "inspireid"}),
    )
    label: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, info={"source": "label"}),
    )
    county: str | None = Field(
        default=None,
        sa_column=Column(String(3), nullable=True, info={"source": "county"}),
    )
    polygon: base_definitions.WKBElementType | None = Field(
        default=None,
        sa_column=Column(Geometry("POLYGON"), info={"source": "_ogr_geometry_"}),
    )
