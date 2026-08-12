from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import get_session_factory
from app.models.manufacturing import (
    Equipment,
    Product,
    ProductInventoryBalance,
    Supplier,
    TeaLeaf,
    Variety,
)

SEED_MASTERS = (
    (TeaLeaf, {"code": "TL-DEMO", "name": "デモ茶葉", "is_active": True}),
    (Variety, {"code": "VR-DEMO", "name": "やぶきた（デモ）", "is_active": True}),
    (Supplier, {"code": "SP-DEMO", "name": "デモ茶園", "is_active": True}),
    (Equipment, {"code": "EQ-DEMO", "name": "デモ蒸機", "is_active": True}),
)


def seed_demo_data() -> None:
    with get_session_factory()() as session, session.begin():
        for model, values in SEED_MASTERS:
            session.execute(
                insert(model)
                .values(**values)
                .on_conflict_do_update(index_elements=[model.code], set_=values)
            )
        variety_id = session.scalar(select(Variety.id).where(Variety.code == "VR-DEMO"))
        product_id = session.scalar(
            insert(Product)
            .values(
                code="PR-DEMO",
                name="デモ煎茶製品",
                variety_id=variety_id,
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[Product.code],
                set_={
                    "name": "デモ煎茶製品",
                    "variety_id": variety_id,
                    "is_active": True,
                },
            )
            .returning(Product.id)
        )
        session.execute(
            insert(ProductInventoryBalance)
            .values(product_id=product_id, quantity=Decimal("0.000"))
            .on_conflict_do_nothing(index_elements=[ProductInventoryBalance.product_id])
        )


if __name__ == "__main__":
    seed_demo_data()
