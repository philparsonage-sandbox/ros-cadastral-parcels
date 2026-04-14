"""Pydantic models for ROS Cadastral Parcels ogrinfo output."""

from typing import ClassVar, Literal
from pydantic import Field
from sandbox_ingest import ogr_model

# --- Schema field models (describe what ogrinfo reports about each field) ---


class CadastralParcelField(ogr_model.OGRField):
    """Valid attribute field names reported by ogrinfo for the ABN_bng layer."""

    name: Literal[
        "inspireid",
        "date_migra",
        "referencep",
        "areavalue",
        "beginlifes",
        "endlifespa",
        "label",
        "nationalca",
        "validfrom",
        "validto",
        "county",
    ]


class CadastralParcelGeometryField(ogr_model.GeometryField):
    """Valid geometry field name reported by ogrinfo for the ABN_bng layer."""

    name: Literal["_ogr_geometry_", ""]


# --- Layer model ---


class CadastralParcelLayer(ogr_model.OGRLayer):
    """OGR layer model for the layer."""

    name: str
    fields: list[CadastralParcelField]
    geometry_fields: list[CadastralParcelGeometryField] = Field(alias="geometryFields")
    geometry_type: ClassVar[str] = "POLYGON"
    value_constraints: ClassVar[dict[str, list[str]]] = {}
    #data_type: ClassVar = ros_cadastral_parcels_definition.CadastralParcel


ROSCadastralParcelsInfo = ogr_model.OGRInfo[CadastralParcelLayer]
