all: test

version=`python -c 'import starchart; print(starchart.__version__)'`

test:
	black starchart tests setup.py --check
	flake8 starchart tests setup.py
	mypy --ignore-missing-imports starchart
	python setup.py pytest

black:
	black starchart tests setup.py

tag:
	git tag $(version) -m "Release of version $(version)"

sdist:
	./setup.py sdist

pypi_release:
	./setup.py sdist upload -r pypi

github_release:
	git push origin --tags && git push

release: tag github_release pypi_release

clean:
	rm -rf .eggs *.egg-info dist build
