def token_generator(token_source, stop_token=None):
    """
    Generator that yields tokens from a source until it encounters a stop token or stop sequence.
    Works with any iterable (lists, generators, streams, etc.).
    
    Args:
        token_source: An iterable that yields tokens (list, generator, stream, etc.)
        stop_token: The token or sequence of tokens that will cause the generator to stop.
                   Can be a single token (str/int) or a list/tuple of tokens for multi-token sequences.
                   If None, yields all tokens from the source.
    
    Yields:
        Tokens from the source until stop_token/stop_sequence is encountered.
    
    Example:
        >>> # Single stop token with a list
        >>> tokens = ['hello', 'world', 'stop', 'more', 'tokens']
        >>> list(token_generator(tokens, stop_token='stop'))
        ['hello', 'world']
        
        >>> # Multi-token stop sequence with a list
        >>> tokens = ['a', 'b', 'c', 'stop', 'here', 'd']
        >>> list(token_generator(tokens, stop_token=['stop', 'here']))
        ['a', 'b', 'c']
        
        >>> # Streaming generator
        >>> def token_stream():
        ...     yield 'hello'
        ...     yield 'world'
        ...     yield 'stop'
        ...     yield 'more'
        >>> list(token_generator(token_stream(), stop_token='stop'))
        ['hello', 'world']
        
        >>> # Multi-token stop with streaming
        >>> def token_stream():
        ...     yield 'a'
        ...     yield 'b'
        ...     yield 'stop'
        ...     yield 'now'
        ...     yield 'c'
        >>> list(token_generator(token_stream(), stop_token=['stop', 'now']))
        ['a', 'b']
    """
    # Normalize stop_token to a list for consistent handling
    if stop_token is None:
        stop_sequence = None
    elif isinstance(stop_token, (str, int)):
        stop_sequence = [stop_token]
    else:
        stop_sequence = list(stop_token)
    
    if stop_sequence is None:
        # No stop sequence, yield all tokens
        yield from token_source
        return
    
    # Buffer to hold tokens for matching multi-token sequences.
    # We buffer tokens before yielding because we need to look ahead to detect
    # multi-token stop sequences. For example, if stop_sequence is ['stop', 'here'],
    # when we see 'stop', we can't yield it immediately - we must check if the next
    # token is 'here'. Only after confirming we don't have a match can we safely
    # yield the oldest buffered token. This ensures we never yield tokens that are
    # part of the stop sequence.
    buffer = []
    stop_len = len(stop_sequence)
    
    for token in token_source:
        buffer.append(token)
        
        # Only check for stop sequence once we have enough tokens in buffer
        if len(buffer) >= stop_len:
            if buffer[-stop_len:] == stop_sequence:
                # Found stop sequence - all tokens before it have already been yielded
                # (via buffer.pop(0) in previous iterations), so we can just stop
                return
            else:
                # Safe to yield the oldest token since we've confirmed it's not
                # the start of a stop sequence
                yield buffer.pop(0)
    
    # Yield any remaining tokens in buffer
    for token in buffer:
        yield token


# Example usage
if __name__ == "__main__":
    # Example 1: List with single stop token
    tokens = ['hello', 'world', 'stop', 'more', 'tokens']
    print("Example 1 - List with single stop token:")
    for token in token_generator(tokens, stop_token='stop'):
        print(f"  {token}")
    
    # Example 2: List with multi-token stop sequence
    tokens = ['hello', 'world', 'stop', 'here', 'more', 'tokens']
    print("\nExample 2 - List with multi-token stop sequence:")
    for token in token_generator(tokens, stop_token=['stop', 'here']):
        print(f"  {token}")
    
    # Example 3: Generator/stream with single stop token
    print("\nExample 3 - Generator with single stop token:")
    def generate_tokens():
        yield 'token1'
        yield 'token2'
        yield 'token3'
        yield '<STOP>'
        yield 'token4'
        yield 'token5'
    
    for token in token_generator(generate_tokens(), stop_token='<STOP>'):
        print(f"  {token}")
    
    # Example 4: Generator/stream with multi-token stop sequence
    print("\nExample 4 - Generator with multi-token stop sequence:")
    def generate_tokens2():
        yield 'a'
        yield 'b'
        yield 'c'
        yield 'stop'
        yield 'now'
        yield 'd'
        yield 'e'
    
    for token in token_generator(generate_tokens2(), stop_token=['stop', 'now']):
        print(f"  {token}")
    
    # Example 5: No stop token (yields all)
    print("\nExample 5 - No stop token (yields all):")
    for token in token_generator(['a', 'b', 'c'], stop_token=None):
        print(f"  {token}")

