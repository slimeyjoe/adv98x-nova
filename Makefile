# SPDX-License-Identifier: GPL-3.0-or-later
# NOVA for the Adv98X engine - GNU Make 4
#
# Everything is the engine's make (its source/Makefile, which lists the targets) run with this
# directory as the game: `make data SRC=...`, `make pack`, `make TARGET=sdl3`, `make test`,
# `make e2e`, `make dist`, ... The engine is the submodule engine/ (clone with
# --recurse-submodules, or `git submodule update --init --recursive`); a tree that holds the
# engine itself has it here.
ENGINE := $(if $(wildcard engine/source/Makefile),engine,.)
ifeq ($(wildcard $(ENGINE)/source/Makefile),)
$(error the engine is missing: git submodule update --init --recursive)
endif
ifeq ($(wildcard $(ENGINE)/source/lrvne/mk/lrvne.mk),)
$(error lrvne is missing: git submodule update --init --recursive)
endif

# the game's release archives are named after it and its version (VERSION)
GAME_DIST := adv98x-nova-$(strip $(shell cat VERSION))

ENGINE_MAKE = $(MAKE) --no-print-directory -C $(ENGINE)/source GAME_DIR=$(CURDIR) GAME_DIST=$(GAME_DIST)

.DEFAULT_GOAL := all
.PHONY: all FORCE
all:
	@$(ENGINE_MAKE)
Makefile: ;
%: FORCE
	@$(ENGINE_MAKE) $@
FORCE: ;
