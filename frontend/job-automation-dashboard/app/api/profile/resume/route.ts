import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const cookies = request.headers.get('cookie') || '';

    const response = await fetch(`${BACKEND_URL}/api/profile/resume`, {
      method: 'GET',
      headers: {
        'Cookie': cookies,
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to download resume' },
        { status: response.status }
      );
    }

    const buffer = await response.arrayBuffer();
    const contentDisposition = response.headers.get('content-disposition') || 'attachment; filename="resume.pdf"';
    
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/octet-stream',
        'Content-Disposition': contentDisposition,
      },
    });
  } catch (error) {
    console.error('Resume download error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const cookies = request.headers.get('cookie') || '';

    const response = await fetch(`${BACKEND_URL}/api/profile/resume`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': cookies,
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to delete resume' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Resume delete error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
