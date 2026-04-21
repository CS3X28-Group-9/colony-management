from locust import HttpUser, task, between
import re


class MouseImportUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Step 0: Load page to get CSRF token
        response = self.client.get("/mouse-import/import/")
        self.csrf_token = response.cookies.get("csrftoken")

    @task
    def full_import_flow(self):
        # STEP 1: Upload file
        with open("mousemetrics/mouse_stocks_2025.xlsx", "rb") as f:
            response = self.client.post(
                "/mouse-import/import/",
                files={
                    "file": (
                        "mouse_stocks_2025.xlsx",
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"project": "Proj2", "csrfmiddlewaretoken": self.csrf_token},
                allow_redirects=False,
            )

        # Extract project ID from redirect
        location = response.headers.get("Location")
        if location is not None:
            match = re.search(r"/import/(\d+)/range/", location)
            if not match:
                return

            project_id = match.group(1)

            # STEP 2: Submit range
            self.client.post(
                f"/mouse-import/import/{project_id}/range/",
                data={
                    "cell_range": "B2:O20",
                    "sheet_name": "",
                    "csrfmiddlewaretoken": self.csrf_token,
                },
            )

            # STEP 3: Column mapping
            self.client.post(
                f"/mouse-import/import/{project_id}/preview/",
                data={
                    "map_box": "Box #",
                    "map_date_of_birth": "DOB",
                    "map_sex": "Sex",
                    "map_tube_number": "ID",
                    "map_coat_colour": "",
                    "map_death_cause": "",
                    "map_death_date": "",
                    "map_death_reason": "",
                    "map_earmark": "Earmark",
                    "map_father": "father",
                    "map_genotype": "genotyped",
                    "map_mother": "mother",
                    "map_notes": "",
                    "map_strain": "Strain",
                    "fixed_strain": "floxed-GASP1",
                    "fixed_new_strain": "",
                    "map_study_plan": "",
                    "csrfmiddlewaretoken": self.csrf_token,
                },
            )

            # STEP 4: Commit
            self.client.post(
                f"/mouse-import/import/{project_id}/commit/",
                data={"csrfmiddlewaretoken": self.csrf_token},
            )
