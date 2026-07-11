import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )
)

from dotenv import load_dotenv
load_dotenv()

from main import app

from app.core.extensions import db

from app.domains.content.models import Content
from app.domains.product.models import Product

from app.domains.content.service.content_access import (
    resolve_content_object
)

from app.domains.content.service import (
    populate_content_search_fields
)

from app.domains.product.service import (
    populate_item_search_fields
)

BATCH_SIZE = 500


def backfill_contents():

    print(
        "\n--- Backfilling Content Search Fields ---"
    )

    offset = 0

    while True:

        contents = (
            Content.query
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )

        if not contents:
            break

        for content in contents:

            target = resolve_content_object(
                content,
                session=db.session
            )

            if not target:
                continue


            content.title = (
                getattr(
                    target,
                    "title",
                    ""
                )
                or ""
            )


            content.preview_text = (
                getattr(
                    target,
                    "description",
                    ""
                )
                or getattr(
                    target,
                    "preview_text",
                    ""
                )
                or getattr(
                    target,
                    "body",
                    ""
                )
                or getattr(
                    target,
                    "content_text",
                    ""
                )
                or ""
            )


            populate_content_search_fields(
                content=content,
                obj=target,
                object_type=content.object_type
            )


        db.session.commit()

        print(
            f"Processed contents: {offset + len(contents)}"
        )

        offset += BATCH_SIZE


def backfill_items():

    print(
        "\n--- Backfilling Product Search Fields ---"
    )

    offset = 0

    while True:

        products = (
            Product.query
            .offset(offset)
            .limit(BATCH_SIZE)
            .all()
        )

        if not products:
            break


        for product in products:

            populate_item_search_fields(
                product
            )


        db.session.commit()

        print(
            f"Processed products: {offset + len(products)}"
        )

        offset += BATCH_SIZE


def backfill():

    with app.app_context():

        backfill_contents()

        backfill_items()

        print(
            "\nDone."
        )


if __name__ == "__main__":
    backfill()