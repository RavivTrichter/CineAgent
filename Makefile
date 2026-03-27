.PHONY: cinema assistant ui test install seed

install:
	pip install -r cinema_api/requirements.txt
	pip install -r assistant/requirements.txt
	pip install -r tests/requirements.txt

cinema:
	cd cinema_api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

assistant:
	cd assistant && uvicorn main:app --host 0.0.0.0 --port 8001 --reload

ui:
	cd assistant && streamlit run streamlit_app.py --server.port 8501

test:
	python3 -m pytest tests/ -v --tb=short

seed:
	rm -f cinema_api/cinema.db
	@echo "Cinema DB deleted. Restart the Cinema API to re-seed."
