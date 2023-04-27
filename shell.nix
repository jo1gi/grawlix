with import <nixpkgs> {};

let
  blackboxprotobuf = python3Packages.buildPythonPackage rec {
    pname = "blackboxprotobuf";
    version = "1.0.1";

    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-IztxTmwkzp0cILhxRioiCvkXfk/sAcG3l6xauGoeHOo=";
    };

    propagatedBuildInputs = with python3Packages; [
      protobuf
    ];

    patchPhase = ''
      sed 's/protobuf==3.10.0/protobuf/' requirements.txt > requirements.txt
    '';

    doCheck = false;
  };
  ebooklib = python3Packages.buildPythonPackage rec {
    pname = "EbookLib";
    version = "0.18";
    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "sha256-OFYmQ6e8lNm/VumTC0kn5Ok7XR0JF/aXpkVNtaHBpTM=";
    };
    propagatedBuildInputs = with python3Packages; [
      six
      lxml
    ];
  };
in
mkShell {
  buildInputs = [
    (python3.withPackages(ps: with ps; [
      appdirs
      beautifulsoup4
      blackboxprotobuf
      ebooklib
      httpx
      importlib-resources
      lxml
      pycryptodome
      rich
      tomli

      # Test
      pytest
      mypy
      types-requests
      types-setuptools

      # Build
      build
      setuptools
      twine
    ]))
  ];
}
