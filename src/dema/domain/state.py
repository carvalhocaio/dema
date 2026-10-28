from enum import StrEnum


class Region(StrEnum):
    NORTH = "north"
    NORTHEAST = "northeast"
    CENTER_WEST = "center_west"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    ABROAD = "abroad"


class State(StrEnum):
    AC = "AC"
    AL = "AL"
    AM = "AM"
    AP = "AP"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MG = "MG"
    MS = "MS"
    MT = "MT"
    PA = "PA"
    PB = "PB"
    PE = "PE"
    PI = "PI"
    PR = "PR"
    RJ = "RJ"
    RN = "RN"
    RO = "RO"
    RR = "RR"
    RS = "RS"
    SC = "SC"
    SE = "SE"
    SP = "SP"
    TO = "TO"
    ZZ = "ZZ"

    @property
    def region(self) -> Region:
        return _REGIONS[self]


_REGIONS: dict[State, Region] = {
    **dict.fromkeys(
        (State.AC, State.AM, State.AP, State.PA, State.RO, State.RR, State.TO),
        Region.NORTH,
    ),
    **dict.fromkeys(
        (
            State.AL,
            State.BA,
            State.CE,
            State.MA,
            State.PB,
            State.PE,
            State.PI,
            State.RN,
            State.SE,
        ),
        Region.NORTHEAST,
    ),
    **dict.fromkeys((State.DF, State.GO, State.MS, State.MT), Region.CENTER_WEST),
    **dict.fromkeys((State.ES, State.MG, State.RJ, State.SP), Region.SOUTHEAST),
    **dict.fromkeys((State.PR, State.RS, State.SC), Region.SOUTH),
    State.ZZ: Region.ABROAD,
}
