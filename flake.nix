{
  description = "dema — dev environment (uv + Makefile) reproducible via Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems =
        f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      # nix develop        -> drops you into the shell below
      # nix develop -c make ci -> runs the full pipeline inside it
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python312 # matches .python-version (3.12), requires-python >=3.12
            pkgs.uv # resolves/locks deps from pyproject.toml + uv.lock
            pkgs.gnumake # Makefile targets (ci, lint, test, ...)
            pkgs.nodejs # pyright-python reuses `node` from PATH instead of downloading one
            pkgs.git # required by uv/pre-commit
          ];

          # Use the interpreter provided by nixpkgs instead of letting uv
          # download its own managed CPython — keeps `uv sync` offline-able.
          UV_PYTHON_PREFERENCE = "only-system";

          shellHook = ''
            # Wheels manylinux baixados pelo uv (numpy, pandas, ...) linkam
            # libstdc++/libgcc_s como numa distro FHS; sem expor essas libs,
            # `import numpy` falha com "libstdc++.so.6: cannot open shared object file".
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc # libstdc++.so.6
              pkgs.libgcc # libgcc_s.so.1
              pkgs.zlib # libz.so.1
            ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

            echo "dema dev shell — python $(${pkgs.python312}/bin/python3 --version 2>&1 | cut -d' ' -f2), uv ${pkgs.uv.version}"
            echo "run: make ci"
          '';
        };
      });

      # nix fmt -> formats the .nix files of this flake
      formatter = forAllSystems (pkgs: pkgs.alejandra);
    };
}
