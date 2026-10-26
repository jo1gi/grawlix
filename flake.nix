{
  description = "grawlix - CLI ebook downloader";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        python3Packages = pkgs.python3Packages;

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

          pyproject = true;
          build-system = [ python3Packages.setuptools ];

          patchPhase = ''
      sed -i 's/protobuf==3.10.0/protobuf/' requirements.txt
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
          pyproject = true;
          build-system = [ python3Packages.setuptools ];
        };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pkgs.python3.withPackages(ps: with ps; [
              platformdirs
              beautifulsoup4
              blackboxprotobuf
              ebooklib
              httpx
              importlib-resources
              lxml
              pycryptodome
              pypdf
              rich
              tomli
              urllib3

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
        };
      });
}
