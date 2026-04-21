"""
Sprint 5 - DGDB Client
========================
Helper class for interacting with the Data Governance Database (HotelDGDB).

Auto-bootstraps:
  - Creates the HotelDGDB database if it doesn't exist (raw SQL - ORMs can't create DBs)
  - Creates ETL_Runs and Validation_Results tables via SQLAlchemy create_all()

All subsequent operations use SQLAlchemy ORM sessions.
"""

import pyodbc
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dgdb.models import Base, ETLRun, ValidationResult


class DGDBClient:
    """
    Client for the Data Governance Database (HotelDGDB).

    Usage:
        dgdb = DGDBClient(server, user, password)
        run_id = dgdb.start_run("Sprint 5 Incremental ETL")
        # ... do ETL work ...
        dgdb.log_validation(run_id, "fk_check", "Verify FK integrity", 1000, 998, 2)
        dgdb.end_run(run_id, "Success", records_processed=5000, records_rejected=12)
    """

    DGDB_NAME = "HotelDGDB"

    def __init__(self, server, user, password):
        self.server = server
        self.user = user
        self.password = password

        # Step 1: Ensure the database exists (raw SQL — ORMs can't create databases)
        self._ensure_database()

        # Step 2: Create SQLAlchemy engine and session factory
        conn_str = (
            f"mssql+pyodbc://{user}:{password}@{server}/{self.DGDB_NAME}"
            f"?driver=ODBC+Driver+17+for+SQL+Server"
            f"&TrustServerCertificate=yes"
            f"&Connection+Timeout=30"
        )
        self.engine = create_engine(conn_str, echo=False)

        # Step 3: Create tables if they don't exist (no-op if they already exist)
        Base.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine)

    def _ensure_database(self):
        """Create the HotelDGDB database if it doesn't exist."""
        try:
            conn = pyodbc.connect(
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};DATABASE=master;"
                f"UID={self.user};PWD={self.password};"
                f"TrustServerCertificate=yes;Connection Timeout=30;"
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"""
                IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{self.DGDB_NAME}')
                BEGIN
                    CREATE DATABASE [{self.DGDB_NAME}]
                END
            """)
            conn.close()
            print(f"  [DGDB] Database '{self.DGDB_NAME}' ready")
        except Exception as e:
            print(f"  [DGDB] Warning: Could not ensure database: {e}")
            raise

    # ----------------------------------------------------------
    # ETL Run Logging
    # ----------------------------------------------------------

    def start_run(self, job_name, notes=None):
        """
        Log the start of an ETL run.
        Returns the run_id for use in subsequent calls.
        """
        session = self.Session()
        try:
            run = ETLRun(
                job_name=job_name,
                start_time=datetime.now(),
                status='Running',
                records_processed=0,
                records_rejected=0,
                notes=notes
            )
            session.add(run)
            session.commit()
            run_id = run.run_id
            print(f"  [DGDB] ETL Run started: run_id={run_id}, job='{job_name}'")
            return run_id
        except Exception as e:
            session.rollback()
            print(f"  [DGDB] Error starting run: {e}")
            raise
        finally:
            session.close()

    def end_run(self, run_id, status, records_processed=0, records_rejected=0, notes=None):
        """
        Update an ETL run with final status and counts.
        """
        session = self.Session()
        try:
            run = session.query(ETLRun).filter_by(run_id=run_id).first()
            if run:
                run.end_time = datetime.now()
                run.duration_seconds = (run.end_time - run.start_time).total_seconds()
                run.status = status
                run.records_processed = records_processed
                run.records_rejected = records_rejected
                if notes:
                    run.notes = (run.notes + '\n' + notes) if run.notes else notes
                session.commit()
                print(f"  [DGDB] ETL Run ended: run_id={run_id}, status='{status}', "
                      f"processed={records_processed:,}, rejected={records_rejected:,}, "
                      f"duration={run.duration_seconds:.1f}s")
            else:
                print(f"  [DGDB] Warning: run_id={run_id} not found")
        except Exception as e:
            session.rollback()
            print(f"  [DGDB] Error ending run: {e}")
            raise
        finally:
            session.close()

    # ----------------------------------------------------------
    # Validation Result Logging
    # ----------------------------------------------------------

    def log_validation(self, run_id, rule_name, rule_description,
                       records_checked, records_passed, records_failed):
        """
        Log a validation rule result tied to an ETL run.
        """
        session = self.Session()
        try:
            result = ValidationResult(
                run_id=run_id,
                rule_name=rule_name,
                rule_description=rule_description,
                executed_at=datetime.now(),
                records_checked=records_checked,
                records_passed=records_passed,
                records_failed=records_failed
            )
            session.add(result)
            session.commit()

            status_icon = "PASS" if records_failed == 0 else "WARN"
            print(f"  [DGDB] [{status_icon}] Validation '{rule_name}': "
                  f"checked={records_checked:,}, passed={records_passed:,}, "
                  f"failed={records_failed:,}")
        except Exception as e:
            session.rollback()
            print(f"  [DGDB] Error logging validation: {e}")
            raise
        finally:
            session.close()

    # ----------------------------------------------------------
    # Query Helpers (for evidence/reporting)
    # ----------------------------------------------------------

    def get_all_runs(self):
        """Retrieve all ETL runs (for evidence reporting)."""
        session = self.Session()
        try:
            runs = session.query(ETLRun).order_by(ETLRun.run_id).all()
            return [(r.run_id, r.job_name, r.start_time, r.end_time,
                     r.duration_seconds, r.status, r.records_processed,
                     r.records_rejected, r.notes) for r in runs]
        finally:
            session.close()

    def get_all_validations(self):
        """Retrieve all validation results (for evidence reporting)."""
        session = self.Session()
        try:
            results = session.query(ValidationResult).order_by(ValidationResult.result_id).all()
            return [(r.result_id, r.run_id, r.rule_name, r.rule_description,
                     r.executed_at, r.records_checked, r.records_passed,
                     r.records_failed) for r in results]
        finally:
            session.close()
