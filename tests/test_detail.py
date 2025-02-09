import re

import pytest
from flask import url_for

from registry.donor.models import Batch, DonorsOverview, Note, Record
from registry.list.models import Medals

from .fixtures import sample_of_rc, skip_if_ignored
from .helpers import login


class TestDetail:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(50))
    def test_detail(self, user, testapp, rodne_cislo):
        """Just a simple test that the detail page loads for some random donors"""
        skip_if_ignored(rodne_cislo)
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        assert res.status_code == 200
        assert "<td></td>" not in res
        # Check that the sum of the donations is eqal to the total count
        donations_list = re.search(r">Počty darování</h[1-6]>.*?</b>", res.text, re.S)
        numbers = re.findall(r"(\d+)[\n<]{1}", donations_list.group())
        numbers = list(map(int, numbers))
        assert sum(numbers[:-1]) == numbers[-1]

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(5))
    def test_save_update_note(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        existing_notes = Note.query.count()
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        # New note
        form = res.forms["noteForm"]
        assert form.fields["note"][0].value == ""
        form.fields["note"][0].value = "Lorem ipsum"
        res = form.submit().follow()
        assert res.status_code == 200
        assert "Poznámka uložena." in res
        assert "Lorem ipsum</textarea>" in res.text
        assert Note.query.count() == existing_notes + 1
        # Update existing
        form = res.forms["noteForm"]
        assert form.fields["note"][0].value == "Lorem ipsum"
        form.fields["note"][0].value += " dolor sit amet,"
        res = form.submit().follow()
        assert res.status_code == 200
        assert "Poznámka uložena." in res
        assert "Lorem ipsum dolor sit amet,</textarea>" in res.text
        assert Note.query.count() == existing_notes + 1

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(5))
    def test_manual_import_prepare(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        last_record = (
            Record.query.join(Batch)
            .filter(Record.rodne_cislo == rodne_cislo)
            .order_by(Batch.imported_at.desc())
            .first()
        )
        login(user, testapp)
        detail = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        import_page = detail.click(description="Připravit manuální import")
        import_form = import_page.forms[0]
        assert import_form.fields["donation_center_id"][0].value == "-1"
        input_data = import_form.fields["input_data"][0].value
        for field in (
            "rodne_cislo",
            "first_name",
            "last_name",
            "address",
            "city",
            "postal_code",
            "kod_pojistovny",
        ):
            assert getattr(last_record, field) + ";" in input_data
        assert ";_POČET_" in input_data


class TestAwardDocument:
    @pytest.mark.parametrize("rodne_cislo", ("391105000", "9701037137", "151008110"))
    def test_award_doc_for_man(self, user, testapp, rodne_cislo):
        overview = DonorsOverview.query.get(rodne_cislo)
        medals = Medals.query.all()
        login(user, testapp)
        for medal in medals:
            doc = testapp.get(
                url_for(
                    "donor.render_award_document", rc=rodne_cislo, medal_slug=medal.slug
                )
            )

            assert f"{rodne_cislo[:6]}/{rodne_cislo[6:]}" in doc
            assert overview.first_name in doc
            assert overview.last_name in doc
            assert "pracovník" in doc
            assert "jeho" in doc
            assert "p." in doc
            assert medal.title not in doc
            assert medal.title_acc in doc
            assert medal.title_instr in doc

    @pytest.mark.parametrize("rodne_cislo", ("0457098862", "0552277759", "0160031652"))
    def test_award_doc_for_woman(self, user, testapp, rodne_cislo):
        rodne_cislo = "095404947"
        overview = DonorsOverview.query.get(rodne_cislo)
        medals = Medals.query.all()
        login(user, testapp)
        for medal in medals:
            doc = testapp.get(
                url_for(
                    "donor.render_award_document", rc=rodne_cislo, medal_slug=medal.slug
                )
            )

            assert f"{rodne_cislo[:6]}/{rodne_cislo[6:]}" in doc
            assert overview.first_name in doc
            assert overview.last_name in doc
            assert "pracovnice" in doc
            assert "její" in doc
            assert "pí" in doc
            assert medal.title not in doc
            assert medal.title_acc in doc
            assert medal.title_instr in doc
