# lc2kcc developer targets. Generated files go in build/.
PY ?= python3
LC2KCC = PYTHONPATH=$(CURDIR)/src $(PY) -m lc2kcc
BUILD = build
COREMARK = third_party/coremark
PORT = ports/coremark
COREMARK_SRCS = $(addprefix $(COREMARK)/,core_list_join.c core_main.c core_matrix.c core_state.c core_util.c) $(PORT)/core_portme.c

.PHONY: test hello coremark-size clean

test:
	PYTHONPATH=$(CURDIR)/src $(PY) -m unittest discover -s tests -t tests -v

$(BUILD):
	mkdir -p $@

# hello world: C -> .as -> lint -> .mc -> simulate
hello: | $(BUILD)
	$(LC2KCC) cc examples/hello.c -o $(BUILD)/hello.as
	$(LC2KCC) lint $(BUILD)/hello.as
	$(LC2KCC) as $(BUILD)/hello.as -o $(BUILD)/hello.mc
	$(LC2KCC) run examples/hello.c

# Native x86-32 -Os size of CoreMark with the LC-2K port (compile only).
coremark-size: | $(BUILD)
	@for f in $(COREMARK_SRCS); do \
		gcc -m32 -Os -fno-stack-protector -fno-pic -w -c -I$(COREMARK) -I$(PORT) \
			'-DFLAGS_STR="native"' -o $(BUILD)/$$(basename $$f .c).o $$f || exit 1; \
	done
	@size $(BUILD)/core_*.o | awk 'NR>1{t+=$$1}END{print "x86-32 text bytes:", t}'
	@for o in $(BUILD)/core_*.o; do objdump -d $$o | grep -cE '^\s+[0-9a-f]+:'; done \
		| awk '{s+=$$1}END{print "x86-32 instructions:", s}'

clean:
	rm -rf $(BUILD)
