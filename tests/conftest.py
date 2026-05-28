import pytest
from ui_defect.schema.models import (
    BBox,
    CanonicalDoc,
    Image,
    SafeArea,
    Screen,
    Viewport,
)


@pytest.fixture()
def minimal_screen() -> Screen:
    return Screen(
        id="scr_test",
        platform="android",
        viewport=Viewport(w=1080, h=2400, dpr=3.0),
        safe_area=SafeArea(top=72, bottom=102),
    )


@pytest.fixture()
def minimal_doc(minimal_screen: Screen) -> CanonicalDoc:
    return CanonicalDoc(
        screen=minimal_screen,
        image=Image(full="fixtures/sample.png", w=1080, h=2400),
    )


@pytest.fixture()
def sample_bbox() -> BBox:
    return BBox(x=24, y=200, w=342, h=48)
