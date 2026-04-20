"""SQLModel table definition for ROS Inspire cadastral parcels.

Defines the CadastralParcel ORM model and the DATA_SOURCE identifier used
to name the target PostGIS table.
"""

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String
from sandbox_ingest import base_definitions, geo_definitions
import info

class CadastralParcel(
    base_definitions.generate_base(info.provider, info.source),  # type: ignore[misc]
    SQLModel,
    geo_definitions.generate_polygon(),  # type: ignore[misc]
    table=True,
):
    """A cadastral parcel"""

    __tablename__ = "_".join([info.provider.name, info.source.name])
    __description__ = __doc__
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
