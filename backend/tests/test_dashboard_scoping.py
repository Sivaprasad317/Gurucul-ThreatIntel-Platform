from datetime import UTC, datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.db.base import Base
from backend.app.models import ThreatGroup, Source, Victim
from backend.app.services.dashboard import DashboardService


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def test_country_and_industry_counts_are_actor_scoped():
    engine = make_db()
    with Session(engine) as db:
        a = ThreatGroup(name="Actor A", slug="a", parser_key="qilin")
        b = ThreatGroup(name="Actor B", slug="b", parser_key="qilin")
        db.add_all([a,b]); db.flush()
        sa = Source(group_id=a.id, name="A", base_url="https://a.invalid")
        sb = Source(group_id=b.id, name="B", base_url="https://b.invalid")
        db.add_all([sa,sb]); db.flush()
        db.add_all([
            Victim(source_id=sa.id, group_id=a.id, name="A1", normalized_name="a1", country_code="US", country_name="United States", industry_code="technology", industry_name="Technology", source_page="x"),
            Victim(source_id=sa.id, group_id=a.id, name="A2", normalized_name="a2", country_code="DE", country_name="Germany", industry_code="technology", industry_name="Technology", source_page="x"),
            Victim(source_id=sb.id, group_id=b.id, name="B1", normalized_name="b1", country_code="FR", country_name="France", industry_code="healthcare", industry_name="Healthcare", source_page="x"),
        ])
        db.commit()
        service = DashboardService(db)
        assert service.countries(a.id) == [{"code":"DE","name":"Germany","count":1},{"code":"US","name":"United States","count":1}]
        assert service.industries(a.id)[0]["name"] == "Technology"
        assert service.overview(a.id)["kpis"]["countries"] == 2
        assert service.overview(a.id)["kpis"]["industries"] == 1
