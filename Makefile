export VERSION=0.6
export PYTHON = python
export PYDOC  = pydoc
export PYTHONPATH='.'
export HELP2MAN=help2man

all:
	$(PYTHON) setup.py build

doc:
	test -d docs/api || mkdir docs/api
	cd docs/api/ ; $(PYDOC) -w ../../

man:
	PYTHONPATH=$(PYTHONPATH) $(HELP2MAN) -N -o docs/man1/snap.1 bin/snaptool

install:
	$(PYTHON) setup.py install --root=$(DESTDIR)
	cp docs/man1/snap.1 $(DESTDIR)/usr/share/man/man1/

clean:
	rm -rfv build
	rm -fv snap/*.pyc
	rm -fv snap/metadata/*.pyc
	rm -fv snap/backends/*.pyc
	rm -fv snap/backends/*/*.pyc

package:
	test -d build || mkdir build
	tar czvf build/snap-${VERSION}.tgz . --exclude=.git --exclude=build --transform='s,./,snap-$(VERSION)/,'

rpm: package
	cp build/snap-$(VERSION).tgz ~/rpmbuild/SOURCES
	rpmbuild -ba snap.spec

deb: clean
	debuild -us -uc -i -b

distclean: clean

test:
	PYTHONPATH=$(PYTHONPAT) ${PYTHON} test/run.py

.PHONY: test
