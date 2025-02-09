from random import randint

import pytest
from flask import url_for

from registry.donor.models import (
    DonationCenter,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
)

from .fixtures import sample_of_rc, skip_if_ignored
from .helpers import login


class TestDonorsOverview:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(100))
    def test_refresh_overview(self, rodne_cislo, test_data_df):
        skip_if_ignored(rodne_cislo)
        # Check of the total amount of donations
        donor_overview = DonorsOverview.query.filter_by(rodne_cislo=rodne_cislo).first()
        last_imports = (
            test_data_df[test_data_df.RC == rodne_cislo]
            .sort_values(by="DATUM_IMPORTU")
            .drop_duplicates(["MISTO_ODBERU"], keep="last")
        )
        total_donations = last_imports.POCET_ODBERU.sum()

        assert donor_overview.donation_count_total == total_donations

        # Check of the partial amounts of donations for each donation center
        donation_centers = DonationCenter.query.all()

        for donation_center_slug in [dc.slug for dc in donation_centers] + ["manual"]:
            try:
                dc_last_count = last_imports.loc[
                    last_imports.MISTO_ODBERU == donation_center_slug, "POCET_ODBERU"
                ].values[0]
            except IndexError:
                dc_last_count = 0
            do_last_count = getattr(
                donor_overview, f"donation_count_{donation_center_slug}"
            )
            assert dc_last_count == do_last_count

        # Check of all other attributes
        last_import = last_imports.tail(1)

        override = DonorsOverride.query.get(rodne_cislo)

        for csv_column, attr in (
            ("JMENO", "first_name"),
            ("PRIJMENI", "last_name"),
            ("ULICE", "address"),
            ("MESTO", "city"),
            ("PSC", "postal_code"),
            ("POJISTOVNA", "kod_pojistovny"),
        ):
            if override and getattr(override, attr):
                assert getattr(donor_overview, attr) == getattr(override, attr)
            else:
                assert last_import[csv_column].values[0] == getattr(
                    donor_overview, attr
                )


class TestIgnore:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_ignore(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        login(user, testapp)
        res = testapp.get(url_for("donor.show_ignored"))
        random_reason = str(randint(11111111, 99999999))

        form = res.forms[0]
        form.fields["rodne_cislo"][0].value = rodne_cislo
        form.fields["reason"][0].value = random_reason

        res = form.submit().follow()

        assert rodne_cislo in res.text
        assert random_reason in res.text
        assert "Dárce ignorován." in res.text

        do = testapp.get(url_for("donor.detail", rc=rodne_cislo), status=302)
        assert do.status_code == 302

        res = do.follow()
        assert res.status_code == 200
        assert "Dárce je ignorován" in res.text

        for _, form in res.forms.items():
            if form.fields["rodne_cislo"][0].value == rodne_cislo:
                unignore_form = form
        res = unignore_form.submit().follow()

        assert rodne_cislo not in res.text
        assert random_reason not in res.text
        assert "Dárce již není ignorován." in res.text

        do = testapp.get(url_for("donor.detail", rc=rodne_cislo), status=200)
        assert do.status_code == 200

    def test_ignore_already_ignored(self, user, testapp):
        login(user, testapp)
        ignored_count = IgnoredDonors.query.count()
        already_ignored_rc = IgnoredDonors.query.first().rodne_cislo
        res = testapp.get(url_for("donor.show_ignored"))
        form = res.forms[0]
        form.fields["rodne_cislo"][0].value = already_ignored_rc
        form.fields["reason"][0].value = "foobarbaz"
        res = form.submit().follow()
        assert "Dárce již je v seznamu ignorovaných" in res
        assert ignored_count == IgnoredDonors.query.count()

    def test_ignore_no_reason(self, user, testapp):
        login(user, testapp)
        ignored_count = IgnoredDonors.query.count()
        rodne_cislo = DonorsOverview.query.order_by(
            DonorsOverview.rodne_cislo.desc()
        ).first()
        res = testapp.get(url_for("donor.show_ignored"))
        form = res.forms[0]
        form.fields["rodne_cislo"][0].value = rodne_cislo
        form.fields["reason"][0].value = ""
        res = form.submit().follow()
        assert "Při přidávání do ignorovaných došlo k chybě" in res
        assert ignored_count == IgnoredDonors.query.count()

    def test_unignore_not_ignored(self, user, testapp):
        login(user, testapp)
        ignored_count = IgnoredDonors.query.count()
        rodne_cislo = DonorsOverview.query.order_by(
            DonorsOverview.rodne_cislo.desc()
        ).first()
        res = testapp.get(url_for("donor.show_ignored"))
        form = res.forms[1]
        form.fields["rodne_cislo"][0].value = rodne_cislo
        res = form.submit().follow()
        assert "Při odebírání ze seznamu ignorovaných dárců došlo k chybě" in res
        assert ignored_count == IgnoredDonors.query.count()


class TestOverride:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(5))
    def test_override(self, user, testapp, rodne_cislo):
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))

        old_data = DonorsOverview.query.get(rodne_cislo)

        # Test save
        form = res.forms["donorsOverrideForm"]
        form["first_name"] = "--First--"
        form["last_name"] = "--Last--"
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert "Jméno: --First--" in res
        assert "Příjmení: --Last--" in res

        # Test repeated save
        form = res.forms["donorsOverrideForm"]
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert "Jméno: --First--" in res
        assert "Příjmení: --Last--" in res

        # Test removing one field's value but keeping the other
        form = res.forms["donorsOverrideForm"]
        form["first_name"] = ""
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert ("Jméno: " + str(old_data.first_name)) in res
        assert "Příjmení: --Last--" in res

        # Test deleting the override
        form = res.forms["donorsOverrideForm"]
        res = form.submit("delete_btn").follow()

        assert "Výjimka smazána" in res
        assert ("Jméno: " + str(old_data.first_name)) in res
        assert ("Příjmení: " + str(old_data.last_name)) in res

    def test_get_overrides_json_endpoint(self, user, testapp):
        login(user, testapp)
        res = testapp.get(url_for("donor.get_overrides"))
        overrides = DonorsOverride.query.all()

        assert len(overrides) == len(res.json)
        for override in res.json.values():
            assert len(DonorsOverview.basic_fields) == len(override)

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(1))
    def test_incorrect_override(self, user, testapp, rodne_cislo):
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        form = res.forms["donorsOverrideForm"]
        form.fields["rodne_cislo"][0].value = "9999999999"
        res = form.submit(name="delete_btn").follow()
        # First follow above tries to redirect us to non-existing donor detail
        # so the second one gives us HTTP/404 and then the home
        # page with the error messages.
        res = res.follow(status=404)
        assert "Není co mazat" in res
        assert "Stránka, kterou hledáte, neexistuje" in res

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(1))
    def test_form_errors(self, user, testapp, rodne_cislo):
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        form = res.forms["donorsOverrideForm"]
        form.fields["postal_code"][0].value = "7380X"
        form.fields["kod_pojistovny"][0].value = "1X0"
        res = form.submit(name="save_btn").follow()
        assert "PSČ - Pole musí obsahovat pouze číslice" in res
        assert "Pojišťovna - Pole musí obsahovat pouze číslice" in res
