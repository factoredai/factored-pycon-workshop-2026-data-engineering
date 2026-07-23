"""Tests for Pillar 4: Orchestration (wires Eyes -> Regex/Brain -> Conscience -> Judge per buyer).

Skipped automatically if apache-airflow is not installed in the local venv.
Run inside Docker: docker compose exec airflow-scheduler pytest /opt/airflow/tests/test_dag.py
"""
airflow = __import__("pytest").importorskip("airflow")

import pytest
from airflow.models import DagBag


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder="dags", include_examples=False)


@pytest.fixture(scope="module")
def dag(dagbag):
    dag_obj = dagbag.get_dag("affidavit_validation")
    assert dag_obj is not None, "DAG 'affidavit_validation' not found"
    return dag_obj


class TestDagImport:
    def test_no_import_errors(self, dagbag):
        assert len(dagbag.import_errors) == 0, f"DAG import errors: {dagbag.import_errors}"

    def test_dag_exists(self, dagbag):
        assert "affidavit_validation" in dagbag.dags


class TestDagStructure:
    def test_task_count(self, dag):
        task_ids = [t.task_id for t in dag.tasks]
        assert "load_source_records" in task_ids
        expected_per_buyer = [
            "download_pdfs", "parse_and_extract",
            "validate_results", "create_review_tickets",
        ]
        for buyer in ["buyer_a", "buyer_b"]:
            for task_name in expected_per_buyer:
                full_id = f"process_{buyer}.{task_name}"
                assert full_id in task_ids, f"Missing task: {full_id}"

    def test_task_group_ids_unique(self, dag):
        group_ids = list(dag.task_group.children.keys())
        assert "process_buyer_a" in group_ids
        assert "process_buyer_b" in group_ids

    def test_topological_sort_succeeds(self, dag):
        order = dag.topological_sort()
        assert len(order) == len(dag.tasks)

    def test_dependencies(self, dag):
        for buyer in ["buyer_a", "buyer_b"]:
            prefix = f"process_{buyer}"
            download = dag.get_task(f"{prefix}.download_pdfs")
            parse = dag.get_task(f"{prefix}.parse_and_extract")
            validate = dag.get_task(f"{prefix}.validate_results")
            tickets = dag.get_task(f"{prefix}.create_review_tickets")

            assert f"{prefix}.parse_and_extract" in [
                t.task_id for t in download.downstream_list
            ]
            assert f"{prefix}.validate_results" in [
                t.task_id for t in parse.downstream_list
            ]
            assert f"{prefix}.create_review_tickets" in [
                t.task_id for t in validate.downstream_list
            ]

        load_sr = dag.get_task("load_source_records")
        load_sr_downstream = [t.task_id for t in load_sr.downstream_list]
        assert "process_buyer_a.validate_results" in load_sr_downstream
        assert "process_buyer_b.validate_results" in load_sr_downstream
