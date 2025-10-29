with import <nixpkgs> {};

let
  blackboxprotobuf = python3Packages.buildPythonPackage rec {
    pname = "bbpb";
    version = "1.4.2";

    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "03446991bc500cfc9dd2049e6cc9489979e157c5ecb793e27936ab3d579d3496";
    };

    propagatedBuildInputs = with python3Packages; [
      protobuf
    ];

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
      beautifulsoup4
      blackboxprotobuf
      ebooklib
      httpx
      importlib-resources
      lxml
      platformdirs
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
