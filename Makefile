Board.swf: *.as
	mxmlc -static-link-runtime-shared-libraries -target-player=11 -swf-version=13 Board.as
	mv Board.swf ai-server/static/Board.swf

all: Board.swf

clean:
	rm -f Board.swf
	rm -f ai-server/static/Board.swf
