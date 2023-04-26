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
in
mkShell {
  buildInputs = [
    (python3.withPackages(ps: with ps; [
      appdirs
      beautifulsoup4
      blackboxprotobuf
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
