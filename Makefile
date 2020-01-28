clean:
	-rm -rf build
	-rm -rf dist
	-rm -rf *.egg-info
	-rm -f tests/.coverage
	-docker rm `docker ps -a -q`
	-docker rmi `docker images -q --filter "dangling=true"`

build: clean
	python setup.py bdist_wheel --universal

uninstall:
	-pip uninstall -y vlab-quota

install: uninstall build
	pip install -U dist/*.whl

test: uninstall install
	cd tests && nosetests -v --with-coverage --cover-package=vlab_quota

images: build
	docker build -f ApiDockerfile -t willnx/vlab-quota-api .
	docker build -f PgsqlDockerfile -t willnx/vlab-quota-db .
	docker build -f WorkerDockerfile -t willnx/vlab-quota-worker .

up:
	docker-compose -p vlabQuota -f docker-compose.yml -f docker-compose.override.yml up --abort-on-container-exit
