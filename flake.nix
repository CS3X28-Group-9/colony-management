{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    inherit (nixpkgs) lib;
    systems = ["x86_64-linux" "aarch64-darwin"];
    eachSystem = f:
      lib.genAttrs systems (system:
        f {
          inherit system;
          pkgs = nixpkgs.legacyPackages.${system};
        });
  in {
    devShells = eachSystem ({pkgs, ...}: {
      default = pkgs.mkShell {
        packages = with pkgs; [python3 uv ruff black];
      };
    });
  };
}
