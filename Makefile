# setting the PATH seems only to work in GNUmake not in BSDmake
PATH := ./pythonenv/bin:$(PATH)
S3BUCKET = s.hdimg.net

default: dependencies check test

hudson: clean dependencies test statistics
	find myplfrontend -name '*.py' | xargs /usr/local/hudorakit/bin/hd_pep8
	/usr/local/hudorakit/bin/hd_pylint -f parseable myplfrontend | tee pylint.out

check:
	-find myplfrontend -name '*.py' | xargs /usr/local/hudorakit/bin/hd_pep8
	-/usr/local/hudorakit/bin/hd_pylint myplfrontend

test:
	python manage.py test --verbosity=1 myplfrontend

dependencies:
	virtualenv pythonenv
	pip -q install -E pythonenv -r requirements.txt
	# the following line is needed for Django applications
	sh -c 'echo p | svn co https://cybernetics.hudora.biz/intern/svn/code/projects/html/trunk/templates generic_templates'

statistics:
	sloccount --wide --details myplfrontend > sloccount.sc

build:
	python setup.py build sdist

upload: build
	rsync dist/* root@cybernetics.hudora.biz:/usr/local/www/apache22/data/nonpublic/eggs/

install: build
	sudo python setup.py install

cdn:
	s3put -a $(AWS_ACCESS_KEY_ID) -s $(AWS_SECRET_ACCESS_KEY) -b $(S3BUCKET) -g public-read -p $(PWD)/static/ static

runserver: dependencies
	python manage.py runserver

clean:
	rm -Rf pythonenv build dist html test.db sloccount.sc pylint.out
	find . -name '*.pyc' -or -name '*.pyo' -delete

.PHONY: test build clean install upload check statistics dependencies
