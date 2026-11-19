"""Report images: bytes are stored in the database (ImageBlob), the uploads directory is
only a cache that is refilled on demand. On Render the container disk is wiped on every
restart / spin-down, so files kept only on disk disappeared after a while."""
import io
import os
import uuid

import structlog
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlmodel import Session, func, select

from app.models.report import ImageBlob, ReportImage

logger = structlog.get_logger().bind(service="images")

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
# Wider than this is never needed: the figure is 127 mm wide in the document
MAX_WIDTH_PX = 2000


def uploads_dir() -> str:
    path = os.getenv("UPLOADS_DIR", "/app/uploads")
    os.makedirs(path, exist_ok=True)
    return path


def local_path(image: ReportImage) -> str:
    return os.path.join(uploads_dir(), image.filename)


def prepare_image(raw: bytes) -> tuple[bytes, str]:
    """Checks the upload is a real image and shrinks it so the database stays small.
    Screenshots stay PNG (crisp text); photos stay JPEG."""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Зображення завелике (максимум 15 МБ)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Файл не є зображенням")

    is_jpeg = img.format == "JPEG"
    img = ImageOps.exif_transpose(img)
    if img.width > MAX_WIDTH_PX:
        img = img.resize((MAX_WIDTH_PX, round(img.height * MAX_WIDTH_PX / img.width)), Image.LANCZOS)

    out = io.BytesIO()
    if is_jpeg:
        img.convert("RGB").save(out, "JPEG", quality=88, optimize=True)
        return out.getvalue(), "jpg"
    if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        img = img.convert("RGBA")
    img.save(out, "PNG", optimize=True)
    return out.getvalue(), "png"


def save_image(session: Session, report_id: int, raw: bytes, section_path: str, caption: str) -> ReportImage:
    data, ext = prepare_image(raw)
    position = session.exec(
        select(func.max(ReportImage.position))
        .where(ReportImage.report_id == report_id, ReportImage.section_path == section_path)
    ).first()
    image = ReportImage(
        report_id=report_id,
        filename=f"{uuid.uuid4()}.{ext}",
        caption=caption,
        section_path=section_path,
        position=(position + 1) if position is not None else 0,
    )
    session.add(image)
    session.flush()  # assigns image.id
    session.add(ImageBlob(image_id=image.id, data=data))
    session.commit()
    session.refresh(image)
    with open(local_path(image), "wb") as f:
        f.write(data)
    logger.info("image_saved", image_id=image.id, bytes_in=len(raw), bytes_stored=len(data))
    return image


def ensure_local(session: Session, image: ReportImage) -> bool:
    """Makes sure the file is in the uploads directory, restoring it from the database.
    An image saved before bytes went to the database is backfilled while its file still exists."""
    path = local_path(image)
    blob = session.get(ImageBlob, image.id)
    if os.path.exists(path):
        if blob is None:
            with open(path, "rb") as f:
                session.add(ImageBlob(image_id=image.id, data=f.read()))
            session.commit()
        return True
    if blob is None:
        return False
    with open(path, "wb") as f:
        f.write(blob.data)
    return True


def ensure_all_local(session: Session, images) -> list[ReportImage]:
    """Images whose bytes are available; the lost ones (old uploads wiped from disk) are skipped."""
    return [img for img in images if ensure_local(session, img)]


def is_available(session: Session, image: ReportImage) -> bool:
    return os.path.exists(local_path(image)) or session.get(ImageBlob, image.id) is not None


def delete_image(session: Session, image: ReportImage, commit: bool = True):
    path = local_path(image)
    blob = session.get(ImageBlob, image.id)
    if blob is not None:
        session.delete(blob)
        session.flush()
    session.delete(image)
    if commit:
        session.commit()
    if os.path.exists(path):
        os.remove(path)


def ordered(images):
    return sorted(images, key=lambda i: (i.position or 0, i.id or 0))
