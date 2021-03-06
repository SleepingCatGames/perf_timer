#pragma once

/*
 * MIT License
 * 
 * Copyright (c) 2021 Jaedyn K Draper
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/*
 * This file is presented as a reference implementation for a performance timer
 * using the perf_timer format. This presentation is a 100% usable implementation
 * of the perf timer; however, it is somewhat naiive about multithreading, using
 * std::mutex to guard events rather than using a more tailored solution such as
 * a concurrent queue. This decision was made to keep the reference implementation as
 * simple as possible, but it should be fairly trivial to change it to use a concurrent queue.
 * 
 * Note that by default, multithreading is not enabled to avoid taking the cost in
 * single-threaded apps. You can control this by defining PERFTIMER_MULTITHREADED
 * to true before including the header, or by modifying the header. (It's recomended
 * to set this in the makefile or other build settings to ensure it's applied consistently
 * to all headers or you may have crashes.)
 * 
 * Additionally, the perf timer *itself* is also disabled by default so that instrumenting
 * your code has zero cost unless you make a build with the perf timer turned on. To turn
 * it on, simply #define PERFTIMER_ENABLED before including the header. (Again, recommended
 * to do this in the makefile.)
 * 
 * Basic usage:
 * 
 * void SomeFunction()
 * {
 *     // This creates a performance timer for this function scope. It's automatically named with
 *     // the function's name and results in an object that will go out of scope when the function
 *     // returns.
 *     PERF_TIMER(g_frameCount);
 * 
 *     // This provides a note, which will appear on the output as an annotation on the frame it's
 *     // associated with. This is helpful for tracking the impact on frame time of certain rare events.
 *     PERF_NOTE("A note!", g_frameCount);
 * 
 *     {
 *         // This creates a block-scope perf timer that will track only the time within
 *         // this specific block of code, and will go out of scope at the closing brace.
 *         ::PerfTimer::PerfTimer blockTimer("Some block", g_frameCount);
 *     }
 * }
 */

#include <stdio.h>
#include <string>
#include <mutex>

#if defined(__GNUC__) || defined(__clang__)
#	define PERFTIMER_PACK( STRUCT ) STRUCT __attribute__((__packed__))
#elif defined(_MSC_VER)
#	define PERFTIMER_PACK( STRUCT ) __pragma( pack(push, 1) ) STRUCT __pragma( pack(pop))
#endif

#if !defined(PERFTIMER_BUFFER_SIZE)
#	include "Windows.h"
#	define PERFTIMER_BUFFER_SIZE 32768
#endif

#if !defined(PERFTIMER_MULTITHREADED)
#	define PERFTIMER_MULTITHREADED false
#endif

#if defined PERFTIMER_ENABLED
#	if defined(_MSC_VER) && !defined(__clang__)
#		define PERF_TIMER(frameId) ::PerfTimer::PerfTimer funcTimer__(__FUNCTION__, (frameId))
#	else
#		define PERF_TIMER(frameId) ::PerfTimer::PerfTimer funcTimer__(__PRETTY_FUNCTION__, (frameId))
#	endif
#	define PERF_NOTE(name, frameId) ::PerfTimer::PerfNote((name), (frameId))
#else
#	define PERF_TIMER(frameId)
#	define PERF_NOTE(name, frameId)
#endif

namespace PerfTimer
{
	enum class EventType : unsigned char
	{
		ENTER_CONTEXT = 0,
		EXIT_CONTEXT = 1,
		NOTE = 2
	};

	PERFTIMER_PACK(
		struct ProfileEvent
		{
			EventType eventType;
			int64_t threadId;
			int32_t frameCount;
			int64_t timestamp;
			char const* name{ nullptr };
		}
	);

	struct ProfileEventBuffer
	{
		ProfileEvent events[PERFTIMER_BUFFER_SIZE]{};
		ProfileEvent* current{ events };
		ProfileEventBuffer* next{ nullptr };
	};

	inline char const* CloneStr(char const* str)
	{
		size_t size = strlen(str);
		char* ret = reinterpret_cast<char*>(malloc(size + 1));
		if (ret == nullptr)
		{
			throw std::runtime_error("Out of memory");
		}
		ret[0] = '\1';
		memcpy(ret + 1, str, size);
		return ret;
	}

	class EventRecorder
	{
	public:
		~EventRecorder()
		{
			Write();
		}

		void AddEvent(ProfileEvent&& event)
		{
			if (!m_enabled)
			{
				return;
			}
#if PERFTIMER_MULTITHREADED
			std::lock_guard<std::mutex> lock(m_mutex);
#endif
			*m_current->current = event;
			++m_current->current;
			if (m_current->current >= (m_current->events + 32768))
			{
				ProfileEventBuffer* newBuffer = new ProfileEventBuffer();
				m_current->next = newBuffer;
				m_current = newBuffer;
			}
			++m_count;
		}

		static EventRecorder& get()
		{
			static EventRecorder recorder;
			return recorder;
		}

		static void Start(std::string const& filename)
		{
			EventRecorder& recorder = EventRecorder::get();
			recorder.m_filename = filename;
			recorder.m_enabled = true;
			recorder.m_first = new ProfileEventBuffer();
			recorder.m_current = recorder.m_first;
		}

		static void End()
		{
			EventRecorder& recorder = EventRecorder::get();
			recorder.m_enabled = false;
			recorder.Write();
			recorder.m_count = 0;
		}

		void Write()
		{
			if (m_count == 0)
			{
				return;
			}
#ifdef _MSC_VER
			FILE* output;
			fopen_s(&output, m_filename.c_str(), "wb");
#else
			FILE* output = fopen(m_filename.c_str(), "wb");
#endif
			if (output == nullptr)
			{
				perror("Could not open perf_timer output file for writing.");
				return;
			}
			int32_t magic = 0xFA57;
			fwrite(&magic, sizeof(magic), 1, output);
			fwrite(&m_count, sizeof(m_count), 1, output);
			ProfileEventBuffer* buffer = m_first;
			while (buffer != nullptr)
			{
				ProfileEvent* event = buffer->events;
				while (event < buffer->current)
				{
					fwrite(event, sizeof(EventType) + sizeof(int64_t) + sizeof(int32_t) + sizeof(int64_t), 1, output);
					int16_t len = static_cast<int16_t>(strlen(event->name));
					fwrite(&len, sizeof(int16_t), 1, output);
					if (event->name[0] == '\1')
					{
						fwrite(event->name + 1, len - 1, 1, output);
						free(reinterpret_cast<void*>(const_cast<char*>(event->name)));
					}
					else
					{
						fwrite(event->name, len, 1, output);
					}
					++event;
				}
				ProfileEventBuffer* oldBuffer = buffer;
				buffer = buffer->next;
				delete oldBuffer;
			}
			fflush(output);
			fclose(output);
		}

	private:

#if PERFTIMER_MULTITHREADED
		std::mutex m_mutex;
#endif
		std::string m_filename;
		ProfileEventBuffer* m_first{ nullptr };
		ProfileEventBuffer* m_current{ nullptr };
		int m_count{ 0 };
		bool m_enabled{ false };
	};

#if defined(_MSC_VER)
	namespace internal_
	{
		inline int64_t GetPerformanceFrequency()
		{
			LARGE_INTEGER frequency;
			QueryPerformanceFrequency(&frequency);
			return frequency.QuadPart;
		}

		template<bool allowInHeader = true>
		struct PerformanceFrequency
		{
			static int64_t value;
		};

		template<bool allowInHeader>
		/*static*/ int64_t PerformanceFrequency<allowInHeader>::value = GetPerformanceFrequency();
	}

	inline int64_t Now()
	{
		LARGE_INTEGER time;

		QueryPerformanceCounter(&time);

		double nanoseconds = time.QuadPart * double(1000LL * 1000LL * 1000LL);
		nanoseconds /= internal_::PerformanceFrequency<>::value;
		return int64_t(nanoseconds);
	}
#elif defined(__GNUC__) || defined(__clang__)
	inline int64_t Now()
	{
		struct timespec ts;
		clock_gettime(CLOCK_REALTIME, &ts);
		int64_t nanosecondResult = ts.tv_sec;
		nanosecondResult *= 1000000000;
		nanosecondResult += ts.tv_nsec;
		return nanosecondResult;
	}
#endif

	struct PerfTimer
	{
		PerfTimer(char const* const name, int32_t frameCount)
			: m_name(name)
			, m_frameCount(frameCount)
		{
#if PERFTIMER_MULTITHREADED
#	ifdef _MSC_VER
			const int64_t threadId = static_cast<int64_t>(GetCurrentThreadId());
#	else
			const int64_t threadId = static_cast<int64_t>(pthread_self());
#	endif
#else
			const int64_t threadId = 0;
#endif
			EventRecorder::get().AddEvent({ EventType::ENTER_CONTEXT, threadId, m_frameCount, Now(), m_name });
		}

		~PerfTimer()
		{
#if PERFTIMER_MULTITHREADED
#	ifdef _MSC_VER
			const int64_t threadId = static_cast<int64_t>(GetCurrentThreadId());
#	else
			const int64_t threadId = static_cast<int64_t>(pthread_self());
#	endif
#else
			const int64_t threadId = 0;
#endif
			EventRecorder::get().AddEvent({ EventType::EXIT_CONTEXT, threadId, m_frameCount, Now(), m_name });
		}

		char const* const m_name;
		int32_t m_frameCount;
	};

	inline void PerfNote(char const* const name, int32_t frameCount)
	{
#if PERFTIMER_MULTITHREADED
#	ifdef _MSC_VER
		const int64_t threadId = static_cast<int64_t>(GetCurrentThreadId());
#	else
		const int64_t threadId = static_cast<int64_t>(pthread_self());
#	endif
#else
		const int64_t threadId = 0;
#endif
		EventRecorder::get().AddEvent({ EventType::NOTE, threadId, frameCount, Now(), name });
	}
}