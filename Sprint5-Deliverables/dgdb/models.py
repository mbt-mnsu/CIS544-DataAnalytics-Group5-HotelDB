"""
Sprint 5 - Data Governance Database (DGDB) ORM Models
======================================================
SQLAlchemy model definitions for the HotelDGDB database.

Tables:
  ETL_Runs           - Logs each execution of the ETL pipeline
  Validation_Results — Logs outcomes of data quality checks

These models are used by DGDBClient for all database interactions.
Table creation is handled automatically via SQLAlchemy's create_all().
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Float, ForeignKey,
    create_engine
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ETLRun(Base):
    """Logs each execution of the ETL pipeline."""
    __tablename__ = 'ETL_Runs'

    run_id              = Column(Integer, primary_key=True, autoincrement=True)
    job_name            = Column(String(200), nullable=False)
    start_time          = Column(DateTime, nullable=False)
    end_time            = Column(DateTime, nullable=True)
    duration_seconds    = Column(Float, nullable=True)
    status              = Column(String(20), nullable=False, default='Running')
    records_processed   = Column(Integer, nullable=False, default=0)
    records_rejected    = Column(Integer, nullable=False, default=0)
    notes               = Column(Text, nullable=True)

    # Relationship to validation results
    validations = relationship('ValidationResult', back_populates='etl_run')

    def __repr__(self):
        return (f"<ETLRun(run_id={self.run_id}, job='{self.job_name}', "
                f"status='{self.status}', processed={self.records_processed})>")


class ValidationResult(Base):
    """Logs the outcomes of data quality checks."""
    __tablename__ = 'Validation_Results'

    result_id           = Column(Integer, primary_key=True, autoincrement=True)
    run_id              = Column(Integer, ForeignKey('ETL_Runs.run_id'), nullable=False)
    rule_name           = Column(String(100), nullable=False)
    rule_description    = Column(String(500), nullable=False)
    executed_at         = Column(DateTime, nullable=False)
    records_checked     = Column(Integer, nullable=False, default=0)
    records_passed      = Column(Integer, nullable=False, default=0)
    records_failed      = Column(Integer, nullable=False, default=0)

    # Relationship back to ETL run
    etl_run = relationship('ETLRun', back_populates='validations')

    def __repr__(self):
        return (f"<ValidationResult(rule='{self.rule_name}', "
                f"checked={self.records_checked}, failed={self.records_failed})>")
