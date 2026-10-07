# Rev. Ikingi Boarding Primary School - static website

Local build: JSON data + Jinja2 templates -> dist/ (plain HTML/CSS/JS). No server-side runtime in production.

    pip install jinja2
    python build.py
    python -m http.server 8000 --directory dist

Deploy: copy the CONTENTS of dist/ into Truehost public_html/.

Content rule: only school-confirmed facts are published. Edit src/data/school.json and drop real documents into
src/static/documents/ (admission-form.pdf, fee-structure.pdf, admission-instructions.pdf, uniform-requirements.pdf,
boarding-requirements.pdf, school-calendar.pdf, parent-information.pdf). Buttons appear only when the file/data exists.